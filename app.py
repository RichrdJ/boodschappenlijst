import os
import re
import sqlite3
import time
from flask import Flask, jsonify, request, g, send_from_directory

from categories import CATEGORIES, DEFAULT_CATEGORY, guess_category, normalize

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


def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
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
        CREATE TABLE IF NOT EXISTS categories (
            key TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            color TEXT NOT NULL,
            position INTEGER NOT NULL
        );
    """)
    if conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
        for i, (key, label, _) in enumerate(CATEGORIES):
            conn.execute("INSERT INTO categories VALUES (?, ?, ?, ?)", (key, label, PALETTE[i % len(PALETTE)], i))
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
    items = [dict(r) for r in db().execute("SELECT * FROM items ORDER BY created").fetchall()]
    items.sort(key=lambda r: (order.get(r["category"], 99), r["created"]))
    return items


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
    conn = db()
    conn.execute("INSERT INTO items (name, category, created) VALUES (?, ?, ?)",
                 (name, categorize(name), time.time()))
    conn.execute("INSERT INTO history (name) VALUES (?) ON CONFLICT(name) DO UPDATE SET uses = uses + 1", (name,))
    conn.commit()
    return jsonify(all_items()), 201


@app.patch("/api/items/<int:item_id>")
def update_item(item_id):
    data = request.json or {}
    conn = db()
    item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not item:
        return jsonify({"error": "Product niet gevonden"}), 404
    if "checked" in data:
        conn.execute("UPDATE items SET checked = ? WHERE id = ?", (1 if data["checked"] else 0, item_id))
    if data.get("category") in category_keys():
        conn.execute("UPDATE items SET category = ? WHERE id = ?", (data["category"], item_id))
        remember(item["name"], data["category"])
    conn.commit()
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
