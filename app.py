import os
import re
import sqlite3
import time
from flask import Flask, jsonify, request, g, send_from_directory

from categories import CATEGORIES, DEFAULT_CATEGORY, guess_category, normalize
from spelling import correct

DB_PATH = os.environ.get("DB_PATH", "boodschappen.db")
app = Flask(__name__, static_folder="static")

PALETTE = ["#3E8E41", "#7BB33A", "#C8423B", "#4A90D9", "#C98A2E", "#1FA3A3", "#8A7FA8",
           "#D4537E", "#E07B24", "#5B6BD6", "#2E8B6E", "#9C6B3F"]


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


MULTI_LIST_TABLES = ("items", "learned", "history", "purchases", "categories")


def _columns(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _undo_accounts_schema(conn):
    """De (teruggedraaide) versie met accounts gaf elke tabel een verplichte kolom list_id.
    Daarmee mislukt elke INSERT van deze versie. Zet die tabellen terug naar één lijst,
    met behoud van alle gegevens. Er wordt eerst een reservekopie gemaakt."""
    if "list_id" not in _columns(conn, "items"):
        return False
    backup = sqlite3.connect(f"{DB_PATH}.backup-{time.strftime('%Y%m%d-%H%M%S')}")
    conn.backup(backup)
    backup.close()
    for t in MULTI_LIST_TABLES:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (t,)).fetchone():
            conn.execute(f"DROP TABLE IF EXISTS {t}_old")
            conn.execute(f"ALTER TABLE {t} RENAME TO {t}_old")
    return True


def _copy_back(conn):
    """Gegevens uit de *_old-tabellen in de nieuwe tabellen zetten (meerdere lijsten worden samengevoegd)."""
    have = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "items_old" in have:
        chk = "checked" if "checked" in _columns(conn, "items_old") else "0"
        conn.execute(f"INSERT INTO items (id, name, category, checked, created) "
                     f"SELECT id, name, category, {chk}, created FROM items_old")
    if "learned_old" in have:
        conn.execute("INSERT OR IGNORE INTO learned (name, category) "
                     "SELECT name, category FROM learned_old ORDER BY list_id")
    if "history_old" in have:
        conn.execute("INSERT INTO history (name, uses) SELECT name, SUM(uses) FROM history_old GROUP BY name")
    if "purchases_old" in have:
        conn.execute("INSERT INTO purchases (id, name, category, bought) "
                     "SELECT id, name, category, bought FROM purchases_old")
    if "categories_old" in have:
        conn.execute("INSERT OR IGNORE INTO categories (key, label, color, position) "
                     "SELECT key, label, color, position FROM categories_old ORDER BY list_id, position")
    for t in MULTI_LIST_TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {t}_old")
    conn.execute("PRAGMA user_version = 0")


def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    restored = _undo_accounts_schema(conn)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            checked INTEGER NOT NULL DEFAULT 0,
            created REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS learned (
            name TEXT PRIMARY KEY,
            category TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS history (
            name TEXT PRIMARY KEY,
            uses INTEGER NOT NULL DEFAULT 1
        );
        -- afgevinkte producten: verdwijnen van de lijst en komen in de historie
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            bought REAL NOT NULL
        );
        -- woorden die je bewust zo wilt houden (niet automatisch verbeteren)
        CREATE TABLE IF NOT EXISTS known_words (
            word TEXT PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS categories (
            key TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            color TEXT NOT NULL,
            position INTEGER NOT NULL
        );
    """)
    if restored:
        _copy_back(conn)
    # oudere databases hebben de kolom 'checked' nog niet: CREATE TABLE IF NOT EXISTS
    # past bestaande tabellen niet aan, dus voeg de kolom hier zelf toe
    cols = {r[1] for r in conn.execute("PRAGMA table_info(items)")}
    if "checked" not in cols:
        conn.execute("ALTER TABLE items ADD COLUMN checked INTEGER NOT NULL DEFAULT 0")
    if conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
        for i, (key, label, _) in enumerate(CATEGORIES):
            conn.execute("INSERT INTO categories VALUES (?, ?, ?, ?)", (key, label, PALETTE[i % len(PALETTE)], i))
    # oude versies bewaarden afgevinkte producten op de lijst: verplaats die naar de historie
    conn.execute("INSERT INTO purchases (name, category, bought) SELECT name, category, created FROM items WHERE checked = 1")
    conn.execute("DELETE FROM items WHERE checked = 1")
    conn.commit()
    conn.close()


def get_categories():
    rows = db().execute("SELECT key, label, color FROM categories ORDER BY position").fetchall()
    return [dict(r) for r in rows]


def category_keys():
    return [c["key"] for c in get_categories()]


def categorize(name):
    row = db().execute("SELECT category FROM learned WHERE name = ?", (normalize(name),)).fetchone()
    cat = row["category"] if row else guess_category(name)
    return cat if cat in category_keys() else DEFAULT_CATEGORY


def all_items():
    order = {k: i for i, k in enumerate(category_keys())}
    items = [dict(r) for r in db().execute("SELECT * FROM items WHERE checked = 0 ORDER BY created").fetchall()]
    items.sort(key=lambda r: (order.get(r["category"], 99), r["created"]))
    return items


def vocabulary():
    """Bekende woorden voor productherkenning: trefwoorden, zelf ingedeelde producten en
    woorden die je bewust hebt behouden."""
    words = {kw for _key, _label, kws in CATEGORIES for kw in kws}
    for (name,) in db().execute("SELECT name FROM learned"):
        words.update(name.split())
    words.update(r[0] for r in db().execute("SELECT word FROM known_words"))
    return words


def on_list(name):
    key = normalize(name)
    return any(normalize(r["name"]) == key for r in db().execute("SELECT name FROM items WHERE checked = 0"))


def bump_history(name, delta):
    conn = db()
    if delta > 0:
        conn.execute("INSERT INTO history (name) VALUES (?) ON CONFLICT(name) DO UPDATE SET uses = uses + 1", (name,))
    else:
        conn.execute("UPDATE history SET uses = uses - 1 WHERE name = ?", (name,))
        conn.execute("DELETE FROM history WHERE name = ? AND uses <= 0", (name,))


def remember(name, category):
    db().execute("INSERT INTO learned (name, category) VALUES (?, ?) "
                 "ON CONFLICT(name) DO UPDATE SET category = excluded.category", (normalize(name), category))


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ---------- producten op de lijst ----------

@app.get("/api/items")
def list_items():
    return jsonify(all_items())


@app.post("/api/items")
def add_item():
    name = (request.json or {}).get("name", "").strip()
    if not name:
        return jsonify({"error": "Geen naam opgegeven"}), 400
    fixed = correct(name, vocabulary())
    if fixed != name and on_list(fixed):
        return jsonify({"items": all_items(), "duplicate": fixed})
    conn = db()
    cur = conn.execute("INSERT INTO items (name, category, created) VALUES (?, ?, ?)",
                       (fixed, categorize(fixed), time.time()))
    bump_history(fixed, +1)
    conn.commit()
    return jsonify({"items": all_items(), "id": cur.lastrowid,
                    "corrected": {"from": name, "to": fixed} if fixed != name else None}), 201


@app.patch("/api/items/<int:item_id>")
def update_item(item_id):
    data = request.json or {}
    conn = db()
    item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not item:
        return jsonify({"error": "Dit product staat niet meer op de lijst"}), 404
    new_name = (data.get("name") or "").strip()
    if new_name and new_name != item["name"]:
        # verbetering terugdraaien: oorspronkelijke naam houden en die woorden voortaan met rust laten
        conn.execute("UPDATE items SET name = ?, category = ? WHERE id = ?", (new_name, categorize(new_name), item_id))
        if data.get("keep"):
            known = vocabulary()
            for w in re.findall(r"[a-zà-ÿ'-]+", new_name.lower()):
                if w not in known:
                    conn.execute("INSERT OR IGNORE INTO known_words (word) VALUES (?)", (w,))
        bump_history(item["name"], -1)
        bump_history(new_name, +1)
        item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if data.get("category") in category_keys():
        conn.execute("UPDATE items SET category = ? WHERE id = ?", (data["category"], item_id))
        remember(item["name"], data["category"])
        item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    purchase_id = None
    if data.get("checked"):
        cur = conn.execute("INSERT INTO purchases (name, category, bought) VALUES (?, ?, ?)",
                           (item["name"], item["category"], time.time()))
        purchase_id = cur.lastrowid
        conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    if data.get("checked"):
        return jsonify({"items": all_items(), "purchase_id": purchase_id})
    return jsonify(all_items())


@app.delete("/api/items/<int:item_id>")
def delete_item(item_id):
    db().execute("DELETE FROM items WHERE id = ?", (item_id,))
    db().commit()
    return jsonify(all_items())


@app.post("/api/clear-checked")
def clear_checked():
    db().execute("DELETE FROM items WHERE checked = 1")
    db().commit()
    return jsonify(all_items())


@app.get("/api/suggestions")
def suggestions():
    """Eerder getypte producten, zonder dubbelen (hoofdletters tellen niet), vaakst gebruikt eerst."""
    merged = {}
    for r in db().execute("SELECT name, uses FROM history ORDER BY uses DESC").fetchall():
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


@app.delete("/api/suggestions/<path:name>")
def delete_suggestion(name):
    conn, key = db(), normalize(name)
    for r in conn.execute("SELECT name FROM history").fetchall():
        if normalize(r["name"]) == key:
            conn.execute("DELETE FROM history WHERE name = ?", (r["name"],))
    conn.commit()
    return suggestions()


@app.get("/api/version")
def version():
    return jsonify({"version": os.environ.get("APP_VERSION", "dev")})


# ---------- historie ----------

@app.get("/api/history")
def history():
    rows = db().execute("SELECT * FROM purchases ORDER BY bought DESC LIMIT 1000").fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/history/<int:pid>/undo")
def undo_purchase(pid):
    """Afvinken ongedaan maken: terug op de lijst, weg uit de historie."""
    conn = db()
    p = conn.execute("SELECT * FROM purchases WHERE id = ?", (pid,)).fetchone()
    if p:
        conn.execute("INSERT INTO items (name, category, created) VALUES (?, ?, ?)", (p["name"], p["category"], time.time()))
        conn.execute("DELETE FROM purchases WHERE id = ?", (pid,))
        conn.commit()
    return jsonify(all_items())


@app.post("/api/history/readd")
def readd():
    """Producten uit de historie opnieuw op de lijst zetten (dubbelen worden overgeslagen)."""
    names = (request.json or {}).get("names", [])
    conn = db()
    on_list = {normalize(r["name"]) for r in conn.execute("SELECT name FROM items WHERE checked = 0")}
    added = 0
    for name in names:
        if normalize(name) in on_list:
            continue
        conn.execute("INSERT INTO items (name, category, created) VALUES (?, ?, ?)", (name, categorize(name), time.time()))
        on_list.add(normalize(name))
        added += 1
    conn.commit()
    return jsonify({"items": all_items(), "added": added})


@app.delete("/api/history/<int:pid>")
def delete_purchase(pid):
    db().execute("DELETE FROM purchases WHERE id = ?", (pid,))
    db().commit()
    return history()


# ---------- categorieën beheren ----------

@app.get("/api/categories")
def list_categories():
    return jsonify(get_categories())


@app.post("/api/categories")
def add_category():
    label = (request.json or {}).get("label", "").strip()
    if not label:
        return jsonify({"error": "Geef de categorie een naam"}), 400
    base = re.sub(r"[^a-z0-9]+", "_", normalize(label)).strip("_") or "cat"
    key, n, keys = base, 2, category_keys()
    while key in keys:
        key, n = f"{base}_{n}", n + 1
    conn = db()
    # nieuwe categorie komt net boven "Overig"
    pos = conn.execute("SELECT position FROM categories WHERE key = ?", (DEFAULT_CATEGORY,)).fetchone()[0]
    conn.execute("UPDATE categories SET position = position + 1 WHERE position >= ?", (pos,))
    conn.execute("INSERT INTO categories VALUES (?, ?, ?, ?)", (key, label, PALETTE[len(keys) % len(PALETTE)], pos))
    conn.commit()
    return jsonify(get_categories()), 201


@app.put("/api/categories")
def save_categories():
    """Ontvangt de volledige lijst in de gewenste volgorde: [{key, label, color}]."""
    data = request.json or []
    existing = set(category_keys())
    keep = [c for c in data if c.get("key") in existing]
    if DEFAULT_CATEGORY not in [c["key"] for c in keep]:
        return jsonify({"error": "Overig kan niet worden verwijderd"}), 400
    conn = db()
    for i, c in enumerate(keep):
        conn.execute("UPDATE categories SET label = ?, color = ?, position = ? WHERE key = ?",
                     ((c.get("label") or "").strip() or c["key"], c.get("color") or "#8A7FA8", i, c["key"]))
    removed = existing - {c["key"] for c in keep}
    for key in removed:
        conn.execute("DELETE FROM categories WHERE key = ?", (key,))
        conn.execute("UPDATE items SET category = ? WHERE category = ?", (DEFAULT_CATEGORY, key))
        conn.execute("DELETE FROM learned WHERE category = ?", (key,))
    conn.commit()
    return jsonify(get_categories())


# ---------- onthouden producten ----------

@app.get("/api/learned")
def list_learned():
    rows = db().execute("SELECT name, category FROM learned ORDER BY name").fetchall()
    return jsonify([dict(r) for r in rows])


@app.put("/api/learned")
def set_learned():
    data = request.json or {}
    name, cat = normalize(data.get("name", "")), data.get("category")
    if not name or cat not in category_keys():
        return jsonify({"error": "Ongeldig product of categorie"}), 400
    remember(name, cat)
    db().commit()
    return list_learned()


@app.delete("/api/learned/<path:name>")
def forget(name):
    db().execute("DELETE FROM learned WHERE name = ?", (normalize(name),))
    db().commit()
    return list_learned()


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
