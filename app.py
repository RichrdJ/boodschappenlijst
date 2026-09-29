import logging
import os
import re
import secrets
import sqlite3
import time
from datetime import timedelta
from functools import wraps

from flask import (Blueprint, Flask, abort, g, jsonify, redirect, render_template, request,
                   send_from_directory, session)
from werkzeug.middleware.proxy_fix import ProxyFix

from auth import auth_bp, enabled_providers, init_auth
from categories import CATEGORIES, DEFAULT_CATEGORY, guess_category, normalize

DB_PATH = os.environ.get("DB_PATH", "boodschappen.db")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
MAX_NAME = 120          # tekens per product, categorie of lijstnaam
MAX_ITEMS = 1000        # producten per lijst
MAX_LISTS = 20          # lijsten per gebruiker
INVITE_DAYS = 7

log = logging.getLogger("boodschappen")
logging.basicConfig(level=logging.INFO)

app = Flask(__name__, static_folder="static")
# achter een reverse proxy (Caddy, Nginx Proxy Manager, Cloudflare Tunnel): https en host doorgeven
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config.update(
    MAX_CONTENT_LENGTH=64 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=PUBLIC_URL.startswith("https://"),
    SESSION_COOKIE_NAME="bl_session",
    PERMANENT_SESSION_LIFETIME=timedelta(days=90),
)

PALETTE = ["#3E8E41", "#7BB33A", "#C8423B", "#4A90D9", "#C98A2E", "#1FA3A3", "#8A7FA8",
           "#D4537E", "#E07B24", "#5B6BD6", "#2E8B6E", "#9C6B3F"]


def load_secret_key():
    """SECRET_KEY uit de omgeving, anders één keer aanmaken en naast de database bewaren."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    path = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "secret_key")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(os.open(path, os.O_WRONLY | os.O_CREAT, 0o600), "w") as f:
            f.write(secrets.token_urlsafe(48))
    with open(path) as f:
        return f.read().strip()


app.secret_key = load_secret_key()


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def db():
    if "db" not in g:
        g.db = connect()
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


# ---------- database ----------

SCHEMA = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        subject TEXT NOT NULL,
        email TEXT,
        name TEXT,
        created REAL NOT NULL,
        UNIQUE (provider, subject)
    );
    CREATE TABLE IF NOT EXISTS lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS members (
        list_id INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role TEXT NOT NULL,               -- 'owner' of 'member'
        added REAL NOT NULL,
        PRIMARY KEY (list_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS invites (
        token TEXT PRIMARY KEY,
        list_id INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
        created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        expires REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        list_id INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        created REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS learned (
        list_id INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        PRIMARY KEY (list_id, name)
    );
    CREATE TABLE IF NOT EXISTS history (
        list_id INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        uses INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (list_id, name)
    );
    -- afgevinkte producten: verdwijnen van de lijst en komen in de historie
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        list_id INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        bought REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS categories (
        list_id INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
        key TEXT NOT NULL,
        label TEXT NOT NULL,
        color TEXT NOT NULL,
        position INTEGER NOT NULL,
        PRIMARY KEY (list_id, key)
    );
    CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS items_list ON items(list_id);
    CREATE INDEX IF NOT EXISTS purchases_list ON purchases(list_id, bought);
    CREATE INDEX IF NOT EXISTS members_user ON members(user_id);
"""
SCHEMA_VERSION = 2


def table_exists(conn, name):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone() is not None


def migrate_single_user(conn):
    """Versie 1 had één lijst zonder gebruikers. Die wordt een gewone lijst die de eigenaar
    (OWNER_EMAIL) bij de eerste keer inloggen overneemt."""
    old = [t for t in ("items", "learned", "history", "purchases", "categories") if table_exists(conn, t)]
    for t in old:
        conn.execute(f"ALTER TABLE {t} RENAME TO old_{t}")
    conn.executescript(SCHEMA)
    lid = conn.execute("INSERT INTO lists (name, created) VALUES ('Boodschappen', ?)", (time.time(),)).lastrowid
    if "items" in old:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(old_items)")]
        if "checked" in cols:
            conn.execute("INSERT INTO purchases (list_id, name, category, bought) "
                         "SELECT ?, name, category, created FROM old_items WHERE checked = 1", (lid,))
            conn.execute("DELETE FROM old_items WHERE checked = 1")
        conn.execute("INSERT INTO items (list_id, name, category, created) SELECT ?, name, category, created FROM old_items", (lid,))
    if "learned" in old:
        conn.execute("INSERT INTO learned SELECT ?, name, category FROM old_learned", (lid,))
    if "history" in old:
        conn.execute("INSERT INTO history SELECT ?, name, uses FROM old_history", (lid,))
    if "purchases" in old:
        conn.execute("INSERT INTO purchases (list_id, name, category, bought) SELECT ?, name, category, bought FROM old_purchases", (lid,))
    if "categories" in old and conn.execute("SELECT COUNT(*) FROM old_categories").fetchone()[0]:
        conn.execute("INSERT INTO categories SELECT ?, key, label, color, position FROM old_categories", (lid,))
    else:
        seed_categories(conn, lid)
    for t in old:
        conn.execute(f"DROP TABLE old_{t}")
    conn.execute("INSERT INTO meta VALUES ('legacy_list', ?)", (str(lid),))
    log.info("Bestaande lijst omgezet naar lijst %s; wordt overgenomen door %s", lid, os.environ.get("OWNER_EMAIL") or "(zet OWNER_EMAIL)")


def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = connect()
    conn.execute("PRAGMA journal_mode = WAL")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < SCHEMA_VERSION:
        conn.execute("PRAGMA foreign_keys = OFF")
        with conn:
            if table_exists(conn, "items") and not table_exists(conn, "users"):
                migrate_single_user(conn)
            else:
                conn.executescript(SCHEMA)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.close()


def seed_categories(conn, lid):
    for i, (key, label, _) in enumerate(CATEGORIES):
        conn.execute("INSERT INTO categories VALUES (?, ?, ?, ?, ?)", (lid, key, label, PALETTE[i % len(PALETTE)], i))


def create_list(conn, uid, name):
    lid = conn.execute("INSERT INTO lists (name, created) VALUES (?, ?)", (name, time.time())).lastrowid
    conn.execute("INSERT INTO members VALUES (?, ?, 'owner', ?)", (lid, uid, time.time()))
    seed_categories(conn, lid)
    return lid


# ---------- gebruikers ----------

def login_user(provider, subject, email, email_verified, name):
    """Aangeroepen door auth.py na een geslaagde Google- of Apple-login."""
    conn = db()
    email = (email or "").strip().lower() or None
    row = conn.execute("SELECT id FROM users WHERE provider = ? AND subject = ?", (provider, subject)).fetchone()
    if row:
        uid = row["id"]
        conn.execute("UPDATE users SET email = COALESCE(?, email), name = COALESCE(?, name) WHERE id = ?", (email, name, uid))
    else:
        uid = conn.execute("INSERT INTO users (provider, subject, email, name, created) VALUES (?, ?, ?, ?, ?)",
                           (provider, subject, email, name, time.time())).lastrowid
    # de lijst van vóór de accounts gaat naar de eigenaar
    legacy = conn.execute("SELECT value FROM meta WHERE key = 'legacy_list'").fetchone()
    owner = os.environ.get("OWNER_EMAIL", "").strip().lower()
    if legacy and owner and email == owner and email_verified:
        conn.execute("INSERT OR IGNORE INTO members VALUES (?, ?, 'owner', ?)", (int(legacy["value"]), uid, time.time()))
        conn.execute("DELETE FROM meta WHERE key = 'legacy_list'")
        log.info("Bestaande lijst overgenomen door gebruiker %s", uid)
    conn.commit()
    session.clear()
    session.permanent = True
    session["uid"] = uid


def current_user():
    uid = session.get("uid")
    if not uid:
        return None
    if "user" not in g:
        g.user = db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    return g.user


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not current_user():
            session.clear()
            return jsonify({"error": "Log opnieuw in"}), 401
        return f(*a, **kw)
    return wrapper


@app.before_request
def csrf_guard():
    """Wijzigingen alleen vanaf onze eigen pagina: geen formulieren of scripts van andere sites."""
    if request.method in ("GET", "HEAD", "OPTIONS") or not request.path.startswith("/api/"):
        return
    if request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
        abort(403)
    if request.headers.get("X-Requested-With") != "boodschappen":
        abort(403)


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("Content-Security-Policy",
                            "default-src 'self'; script-src 'self'; "
                            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                            "font-src https://fonts.gstatic.com; img-src 'self' data:; "
                            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    if app.config["SESSION_COOKIE_SECURE"]:
        resp.headers["Strict-Transport-Security"] = "max-age=31536000"
    return resp


def fail(msg, code=400):
    resp = jsonify({"error": msg})
    resp.status_code = code
    abort(resp)


def clean(s, what="naam"):
    s = (s or "").strip() if isinstance(s, str) else ""
    if len(s) > MAX_NAME:
        fail(f"Die {what} is te lang")
    return s


@app.errorhandler(403)
def forbidden(_):
    return jsonify({"error": "Dat mag niet"}), 403


@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Niet gevonden"}), 404
    return redirect("/")


# ---------- pagina's ----------

@app.get("/")
def index():
    if not current_user():
        return render_template("login.html", **login_context())
    return send_from_directory(app.static_folder, "index.html")


LOGIN_ERRORS = {"toegang": "Dit account heeft geen toegang.", "mislukt": "Inloggen is niet gelukt. Probeer het opnieuw."}


def login_context(invite=None, error=None):
    return {"providers": enabled_providers(), "invite": invite, "error": error or LOGIN_ERRORS.get(request.args.get("fout"))}


@app.get("/join/<token>")
def join(token):
    conn = db()
    inv = conn.execute("SELECT i.*, l.name AS list_name, u.name AS by_name, u.email AS by_email FROM invites i "
                       "JOIN lists l ON l.id = i.list_id JOIN users u ON u.id = i.created_by "
                       "WHERE token = ? AND expires > ?", (token, time.time())).fetchone()
    if not inv:
        if current_user():
            return redirect("/?uitnodiging=verlopen")
        return render_template("login.html", **login_context(error="Deze uitnodiging is verlopen of al gebruikt. Vraag om een nieuwe link."))
    user = current_user()
    if not user:
        session["join"] = token
        return render_template("login.html", **login_context(invite={"list": inv["list_name"], "by": inv["by_name"] or inv["by_email"]}))
    conn.execute("INSERT OR IGNORE INTO members VALUES (?, ?, 'member', ?)", (inv["list_id"], user["id"], time.time()))
    conn.execute("DELETE FROM invites WHERE token = ?", (token,))
    conn.commit()
    session.pop("join", None)
    return redirect(f"/?lijst={inv['list_id']}&welkom=1")


# ---------- account en lijsten ----------

def my_lists():
    rows = db().execute("""
        SELECT l.id, l.name, m.role,
               (SELECT COUNT(*) FROM members WHERE list_id = l.id) AS members,
               (SELECT COUNT(*) FROM items WHERE list_id = l.id) AS items
        FROM lists l JOIN members m ON m.list_id = l.id
        WHERE m.user_id = ? ORDER BY m.added""", (session["uid"],)).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/me")
@login_required
def me():
    u = current_user()
    return jsonify({"id": u["id"], "name": u["name"], "email": u["email"], "provider": u["provider"]})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.delete("/api/me")
@login_required
def delete_account():
    """Account weg: eigen lijsten (ook voor wie meedeed) en lidmaatschappen gaan mee."""
    conn, uid = db(), session["uid"]
    conn.execute("DELETE FROM lists WHERE id IN (SELECT list_id FROM members WHERE user_id = ? AND role = 'owner')", (uid,))
    conn.execute("DELETE FROM users WHERE id = ?", (uid,))
    conn.commit()
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/lists")
@login_required
def list_lists():
    lists = my_lists()
    if not lists:
        create_list(db(), session["uid"], "Boodschappen")
        db().commit()
        lists = my_lists()
    return jsonify(lists)


@app.post("/api/lists")
@login_required
def new_list():
    name = clean((request.json or {}).get("name")) or "Boodschappen"
    if len(my_lists()) >= MAX_LISTS:
        return jsonify({"error": f"Je kunt maximaal {MAX_LISTS} lijsten hebben"}), 400
    lid = create_list(db(), session["uid"], name)
    db().commit()
    return jsonify({"id": lid, "lists": my_lists()}), 201


# ---------- alles binnen één lijst ----------

bp = Blueprint("list", __name__, url_prefix="/api/lists/<int:lid>")


@bp.url_value_preprocessor
def pull_list(_endpoint, values):
    g.lid = values.pop("lid")


@bp.before_request
def check_member():
    if not current_user():
        session.clear()
        return jsonify({"error": "Log opnieuw in"}), 401
    row = db().execute("SELECT role FROM members WHERE list_id = ? AND user_id = ?", (g.lid, session["uid"])).fetchone()
    if not row:
        return jsonify({"error": "Je doet niet (meer) mee met deze lijst", "code": "not_member"}), 404
    g.role = row["role"]


def owner_only():
    if g.role != "owner":
        abort(403)


def get_categories():
    rows = db().execute("SELECT key, label, color FROM categories WHERE list_id = ? ORDER BY position", (g.lid,)).fetchall()
    return [dict(r) for r in rows]


def category_keys():
    return [c["key"] for c in get_categories()]


def categorize(name):
    row = db().execute("SELECT category FROM learned WHERE list_id = ? AND name = ?", (g.lid, normalize(name))).fetchone()
    cat = row["category"] if row else guess_category(name)
    return cat if cat in category_keys() else DEFAULT_CATEGORY


def all_items():
    order = {k: i for i, k in enumerate(category_keys())}
    rows = db().execute("SELECT id, name, category, created FROM items WHERE list_id = ? ORDER BY created", (g.lid,)).fetchall()
    items = [dict(r) for r in rows]
    items.sort(key=lambda r: (order.get(r["category"], 99), r["created"]))
    return items


def get_item(item_id):
    return db().execute("SELECT * FROM items WHERE id = ? AND list_id = ?", (item_id, g.lid)).fetchone()


def remember(name, category):
    db().execute("INSERT INTO learned (list_id, name, category) VALUES (?, ?, ?) "
                 "ON CONFLICT(list_id, name) DO UPDATE SET category = excluded.category", (g.lid, normalize(name), category))


def add_to_list(name):
    conn = db()
    if conn.execute("SELECT COUNT(*) FROM items WHERE list_id = ?", (g.lid,)).fetchone()[0] >= MAX_ITEMS:
        fail("Je lijst is vol")
    conn.execute("INSERT INTO items (list_id, name, category, created) VALUES (?, ?, ?, ?)",
                 (g.lid, name, categorize(name), time.time()))


# ---------- de lijst zelf: naam, leden, uitnodigen ----------

@bp.get("")
def list_info():
    conn = db()
    lst = conn.execute("SELECT id, name FROM lists WHERE id = ?", (g.lid,)).fetchone()
    members = conn.execute("SELECT u.id, u.name, u.email, m.role FROM members m JOIN users u ON u.id = m.user_id "
                           "WHERE m.list_id = ? ORDER BY m.added", (g.lid,)).fetchall()
    return jsonify({"id": lst["id"], "name": lst["name"], "role": g.role, "me": session["uid"],
                    "members": [dict(m) for m in members]})


@bp.patch("")
def rename_list():
    name = clean((request.json or {}).get("name"))
    if not name:
        return jsonify({"error": "Geef de lijst een naam"}), 400
    db().execute("UPDATE lists SET name = ? WHERE id = ?", (name, g.lid))
    db().commit()
    return list_info()


@bp.delete("")
def delete_list():
    owner_only()
    db().execute("DELETE FROM lists WHERE id = ?", (g.lid,))
    db().commit()
    return jsonify({"ok": True})


@bp.post("/invites")
def create_invite():
    """Eenmalige link, een week geldig. Iedereen op de lijst mag iemand uitnodigen."""
    conn, token = db(), secrets.token_urlsafe(24)
    conn.execute("DELETE FROM invites WHERE expires < ?", (time.time(),))
    if conn.execute("SELECT COUNT(*) FROM invites WHERE list_id = ?", (g.lid,)).fetchone()[0] >= 20:
        return jsonify({"error": "Er staan al veel uitnodigingen open. Probeer het later opnieuw."}), 400
    conn.execute("INSERT INTO invites VALUES (?, ?, ?, ?)", (token, g.lid, session["uid"], time.time() + INVITE_DAYS * 86400))
    conn.commit()
    base = PUBLIC_URL or request.host_url.rstrip("/")
    return jsonify({"url": f"{base}/join/{token}", "days": INVITE_DAYS}), 201


@bp.delete("/members/<int:uid>")
def remove_member(uid):
    """Zelf vertrekken mag altijd (behalve als eigenaar), anderen verwijderen alleen de eigenaar."""
    if uid == session["uid"]:
        if g.role == "owner":
            return jsonify({"error": "Als eigenaar kun je de lijst alleen verwijderen"}), 400
    else:
        owner_only()
    db().execute("DELETE FROM members WHERE list_id = ? AND user_id = ? AND role != 'owner'", (g.lid, uid))
    db().commit()
    return jsonify({"ok": True}) if uid == session["uid"] else list_info()


# ---------- producten op de lijst ----------

@bp.get("/items")
def list_items():
    return jsonify(all_items())


@bp.post("/items")
def add_item():
    name = clean((request.json or {}).get("name"))
    if not name:
        return jsonify({"error": "Geen naam opgegeven"}), 400
    add_to_list(name)
    db().execute("INSERT INTO history (list_id, name) VALUES (?, ?) "
                 "ON CONFLICT(list_id, name) DO UPDATE SET uses = uses + 1", (g.lid, name))
    db().commit()
    return jsonify(all_items()), 201


@bp.patch("/items/<int:item_id>")
def update_item(item_id):
    data = request.json or {}
    conn = db()
    item = get_item(item_id)
    if not item:
        return jsonify({"error": "Dit product staat niet meer op de lijst"}), 404
    if data.get("category") in category_keys():
        conn.execute("UPDATE items SET category = ? WHERE id = ?", (data["category"], item_id))
        remember(item["name"], data["category"])
        item = get_item(item_id)
    purchase_id = None
    if data.get("checked"):
        cur = conn.execute("INSERT INTO purchases (list_id, name, category, bought) VALUES (?, ?, ?, ?)",
                           (g.lid, item["name"], item["category"], time.time()))
        purchase_id = cur.lastrowid
        conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    if data.get("checked"):
        return jsonify({"items": all_items(), "purchase_id": purchase_id})
    return jsonify(all_items())


@bp.delete("/items/<int:item_id>")
def delete_item(item_id):
    db().execute("DELETE FROM items WHERE id = ? AND list_id = ?", (item_id, g.lid))
    db().commit()
    return jsonify(all_items())


@bp.get("/suggestions")
def suggestions():
    """Eerder getypte producten, zonder dubbelen (hoofdletters tellen niet), vaakst gebruikt eerst."""
    merged = {}
    for r in db().execute("SELECT name, uses FROM history WHERE list_id = ? ORDER BY uses DESC", (g.lid,)).fetchall():
        key = normalize(r["name"])
        if not key:
            continue
        if key in merged:
            merged[key]["uses"] += r["uses"]
        else:
            merged[key] = {"name": r["name"], "uses": r["uses"]}
    result = sorted(merged.values(), key=lambda x: -x["uses"])[:500]
    for x in result:
        x["category"] = categorize(x["name"])
    return jsonify(result)


@bp.delete("/suggestions/<path:name>")
def delete_suggestion(name):
    conn, key = db(), normalize(name)
    for r in conn.execute("SELECT name FROM history WHERE list_id = ?", (g.lid,)).fetchall():
        if normalize(r["name"]) == key:
            conn.execute("DELETE FROM history WHERE list_id = ? AND name = ?", (g.lid, r["name"]))
    conn.commit()
    return suggestions()


@app.get("/api/version")
def version():
    return jsonify({"version": os.environ.get("APP_VERSION", "dev")})


# ---------- historie ----------

@bp.get("/history")
def history():
    rows = db().execute("SELECT id, name, category, bought FROM purchases WHERE list_id = ? "
                        "ORDER BY bought DESC LIMIT 1000", (g.lid,)).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.post("/history/<int:pid>/undo")
def undo_purchase(pid):
    """Afvinken ongedaan maken: terug op de lijst, weg uit de historie."""
    conn = db()
    p = conn.execute("SELECT * FROM purchases WHERE id = ? AND list_id = ?", (pid, g.lid)).fetchone()
    if p:
        conn.execute("INSERT INTO items (list_id, name, category, created) VALUES (?, ?, ?, ?)",
                     (g.lid, p["name"], p["category"], time.time()))
        conn.execute("DELETE FROM purchases WHERE id = ?", (pid,))
        conn.commit()
    return jsonify(all_items())


@bp.post("/history/readd")
def readd():
    """Producten uit de historie opnieuw op de lijst zetten (dubbelen worden overgeslagen)."""
    names = (request.json or {}).get("names", [])
    if not isinstance(names, list):
        return jsonify({"error": "Ongeldige invoer"}), 400
    conn = db()
    on_list = {normalize(r["name"]) for r in conn.execute("SELECT name FROM items WHERE list_id = ?", (g.lid,))}
    added = 0
    for name in names[:200]:
        name = clean(name)
        if not name or normalize(name) in on_list:
            continue
        add_to_list(name)
        on_list.add(normalize(name))
        added += 1
    conn.commit()
    return jsonify({"items": all_items(), "added": added})


@bp.delete("/history/<int:pid>")
def delete_purchase(pid):
    db().execute("DELETE FROM purchases WHERE id = ? AND list_id = ?", (pid, g.lid))
    db().commit()
    return history()


# ---------- categorieën beheren ----------

@bp.get("/categories")
def list_categories():
    return jsonify(get_categories())


@bp.post("/categories")
def add_category():
    label = clean((request.json or {}).get("label"), "categorienaam")
    if not label:
        return jsonify({"error": "Geef de categorie een naam"}), 400
    base = re.sub(r"[^a-z0-9]+", "_", normalize(label)).strip("_") or "cat"
    key, n, keys = base, 2, category_keys()
    if len(keys) >= 50:
        return jsonify({"error": "Dat zijn wel heel veel categorieën"}), 400
    while key in keys:
        key, n = f"{base}_{n}", n + 1
    conn = db()
    # nieuwe categorie komt net boven "Overig"
    pos = conn.execute("SELECT position FROM categories WHERE list_id = ? AND key = ?", (g.lid, DEFAULT_CATEGORY)).fetchone()[0]
    conn.execute("UPDATE categories SET position = position + 1 WHERE list_id = ? AND position >= ?", (g.lid, pos))
    conn.execute("INSERT INTO categories VALUES (?, ?, ?, ?, ?)", (g.lid, key, label, PALETTE[len(keys) % len(PALETTE)], pos))
    conn.commit()
    return jsonify(get_categories()), 201


COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


@bp.put("/categories")
def save_categories():
    """Ontvangt de volledige lijst in de gewenste volgorde: [{key, label, color}]."""
    data = request.json
    if not isinstance(data, list) or not all(isinstance(c, dict) for c in data):
        return jsonify({"error": "Ongeldige invoer"}), 400
    existing = set(category_keys())
    keep = [c for c in data if c.get("key") in existing]
    if DEFAULT_CATEGORY not in [c["key"] for c in keep]:
        return jsonify({"error": "Overig kan niet worden verwijderd"}), 400
    conn = db()
    for i, c in enumerate(keep):
        color = c.get("color") if COLOR.match(str(c.get("color", ""))) else "#8A7FA8"
        conn.execute("UPDATE categories SET label = ?, color = ?, position = ? WHERE list_id = ? AND key = ?",
                     (clean(c.get("label"), "categorienaam") or c["key"], color, i, g.lid, c["key"]))
    removed = existing - {c["key"] for c in keep}
    for key in removed:
        conn.execute("DELETE FROM categories WHERE list_id = ? AND key = ?", (g.lid, key))
        conn.execute("UPDATE items SET category = ? WHERE list_id = ? AND category = ?", (DEFAULT_CATEGORY, g.lid, key))
        conn.execute("DELETE FROM learned WHERE list_id = ? AND category = ?", (g.lid, key))
    conn.commit()
    return jsonify(get_categories())


# ---------- onthouden producten ----------

@bp.get("/learned")
def list_learned():
    rows = db().execute("SELECT name, category FROM learned WHERE list_id = ? ORDER BY name", (g.lid,)).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.put("/learned")
def set_learned():
    data = request.json or {}
    name, cat = normalize(clean(data.get("name"))), data.get("category")
    if not name or cat not in category_keys():
        return jsonify({"error": "Ongeldig product of categorie"}), 400
    remember(name, cat)
    db().commit()
    return list_learned()


@bp.delete("/learned/<path:name>")
def forget(name):
    db().execute("DELETE FROM learned WHERE list_id = ? AND name = ?", (g.lid, normalize(name)))
    db().commit()
    return list_learned()


app.register_blueprint(bp)
app.register_blueprint(auth_bp)
init_auth(app, login_user)
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
