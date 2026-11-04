"""Sreevija Vastara – Flask + SQLite backend (also serves the storefront)."""
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

BASE = Path(__file__).parent
DB_PATH = os.environ.get("DB_PATH", str(BASE / "shop.db"))
UPLOADS = BASE / "uploads"
UPLOADS.mkdir(exist_ok=True)
FREE_SHIP, SHIP_FEE = 1999, 99
SESSION_TTL = 60 * 60 * 24 * 14
ORDER_STATUSES = ["Placed", "Confirmed", "Shipped", "Delivered", "Cancelled"]
PAY_METHODS = ["UPI", "Credit / Debit Card", "Net Banking", "Cash on Delivery"]

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL, is_admin INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(
  token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, expires_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS products(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, fabric TEXT NOT NULL,
  color TEXT NOT NULL, occasion TEXT NOT NULL, price INTEGER NOT NULL CHECK(price>=0),
  mrp INTEGER NOT NULL CHECK(mrp>=0), rating REAL NOT NULL DEFAULT 4.5, stock INTEGER NOT NULL DEFAULT 0 CHECK(stock>=0),
  colors TEXT NOT NULL DEFAULT '["#f4c2d0","#f3d9a4"]', description TEXT NOT NULL DEFAULT '',
  image TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS wishlist(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  PRIMARY KEY(user_id, product_id));
CREATE TABLE IF NOT EXISTS orders(
  id TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id), name TEXT NOT NULL, phone TEXT NOT NULL,
  email TEXT NOT NULL, address TEXT NOT NULL, city TEXT NOT NULL, pincode TEXT NOT NULL,
  payment_method TEXT NOT NULL, payment_status TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Placed',
  subtotal INTEGER NOT NULL, shipping INTEGER NOT NULL, total INTEGER NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS order_items(
  id INTEGER PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id INTEGER NOT NULL, name TEXT NOT NULL, price INTEGER NOT NULL, qty INTEGER NOT NULL);
"""

SEED = [
    ("Royal Kanjivaram Silk", "Kanjivaram", "Pure Silk", "Rose", "Wedding", 12999, 15999, 4.8, 5, ["#e8a0b4", "#f3d9a4"], "Handwoven pure zari Kanjivaram with temple border and rich pallu."),
    ("Soft Silk Gold Zari", "Silk", "Silk Blend", "Gold", "Festive", 8999, 10999, 4.6, 8, ["#f3d9a4", "#e8cfa0"], "Lightweight soft silk with graceful gold zari motifs."),
    ("Kanjivaram Temple Border Mint", "Kanjivaram", "Pure Silk", "Mint", "Festive", 9499, 11499, 4.5, 7, ["#a8d5c2", "#f3d9a4"], "Pure Kanjivaram in mint with a contrast temple border."),
    ("Mysore Silk Emerald", "Silk", "Pure Silk", "Green", "Festive", 6499, 7999, 4.7, 12, ["#a8d5c2", "#f3d9a4"], "Lustrous Mysore crepe silk with contrast border."),
    ("Chanderi Pastel Pink", "Silk", "Silk Blend", "Pink", "Party", 3499, 4499, 4.4, 15, ["#f4c2d0", "#fdeef2"], "Light and sheer silk with delicate buttis."),
    ("Soft Silk Butter Yellow", "Silk", "Silk Blend", "Yellow", "Festive", 4299, 5299, 4.5, 20, ["#f6d98a", "#f0c97a"], "Soft silk with a woven border, ideal for festive days."),
    ("Bridal Kanjivaram Rose", "Bridal", "Pure Silk", "Pink", "Wedding", 15999, 19999, 4.9, 3, ["#f2a7a7", "#f5dd9e"], "Statement bridal Kanjivaram with heavy zari work."),
    ("Kanjivaram Lavender Checks", "Kanjivaram", "Pure Silk", "Lavender", "Festive", 10999, 12999, 4.6, 6, ["#c9b6e4", "#f3d9a4"], "Soft lavender Kanjivaram with gold checks."),
    ("Bridal Peach Zari Silk", "Bridal", "Pure Silk", "Peach", "Wedding", 18999, 22999, 4.8, 4, ["#f6c9b3", "#f3d9a4"], "Rich bridal silk with full zari body and wide border."),
    ("Bridal Ivory Silk", "Bridal", "Pure Silk", "White", "Wedding", 7499, 8999, 4.5, 9, ["#f7efe0", "#e6d2a8"], "Ivory bridal silk with understated gold border."),
    ("Dharmavaram Pattu Peach Zari", "Dharmavaram", "Pure Silk", "Peach", "Wedding", 11499, 13999, 4.7, 6, ["#f6c9b3", "#f3d9a4"], "Traditional Dharmavaram pattu with a broad zari border and rich pallu."),
    ("Dharmavaram Pastel Green Pattu", "Dharmavaram", "Pure Silk", "Green", "Festive", 9999, 11999, 4.6, 8, ["#b9d3b4", "#f3d9a4"], "Handwoven Dharmavaram silk in soft green with contrast border."),
    ("Dharmavaram Rose Temple Border", "Dharmavaram", "Pure Silk", "Rose", "Festive", 10499, 12499, 4.5, 5, ["#f4c2d0", "#e8cfa0"], "Rose Dharmavaram with a temple-motif border."),
]


# ---------- db ----------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, isolation_level=None)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    if not conn.execute("SELECT 1 FROM products LIMIT 1").fetchone():
        now = time.time()
        for i, s in enumerate(SEED):
            conn.execute(
                "INSERT INTO products(name,category,fabric,color,occasion,price,mrp,rating,stock,colors,description,created_at)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (*s[:9], json.dumps(s[9]), s[10], now + i),
            )
    if not conn.execute("SELECT 1 FROM users WHERE is_admin=1").fetchone():
        email = os.environ.get("ADMIN_EMAIL", "admin@sreevijavastara.com")
        pw = os.environ.get("ADMIN_PASSWORD") or secrets.token_urlsafe(9)
        conn.execute(
            "INSERT INTO users(name,email,password_hash,is_admin,created_at) VALUES(?,?,?,1,?)",
            ("Admin", email, generate_password_hash(pw), time.time()),
        )
        print(f"\n*** Admin account created: {email} / {pw}  (shown once, store it) ***\n", flush=True)
    conn.commit()
    conn.close()


# ---------- helpers ----------
def err(msg, code=400):
    return jsonify(error=msg), code


def product_json(r):
    d = dict(r)
    d["colors"] = json.loads(d["colors"])
    d["date"] = d.pop("created_at")
    d.pop("active", None)
    return d


def current_user():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    row = db().execute(
        "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires_at>?",
        (auth[7:], time.time()),
    ).fetchone()
    return row


def login_required(admin=False):
    def deco(fn):
        @wraps(fn)
        def wrap(*a, **kw):
            u = current_user()
            if not u:
                return err("Login required", 401)
            if admin and not u["is_admin"]:
                return err("Admin only", 403)
            g.user = u
            return fn(*a, **kw)
        return wrap
    return deco


def new_session(user_id):
    token = secrets.token_urlsafe(32)
    db().execute("INSERT INTO sessions VALUES(?,?,?)", (token, user_id, time.time() + SESSION_TTL))
    return token


def user_json(u):
    return {"id": u["id"], "name": u["name"], "email": u["email"], "isAdmin": bool(u["is_admin"])}


def body():
    return request.get_json(silent=True) or {}


def clean_product(data, partial=False):
    """Validate admin product input. Returns (dict, error)."""
    out = {}
    for k in ("name", "category", "fabric", "color", "occasion"):
        if k in data or not partial:
            v = str(data.get(k, "")).strip()
            if not v or len(v) > 100:
                return None, f"Invalid {k}"
            out[k] = v
    for k in ("price", "mrp", "stock"):
        if k in data or not partial:
            try:
                v = int(data.get(k))
            except (TypeError, ValueError):
                return None, f"Invalid {k}"
            if v < 0 or v > 10_000_000:
                return None, f"Invalid {k}"
            out[k] = v
    if "rating" in data:
        try:
            out["rating"] = max(0.0, min(5.0, float(data["rating"])))
        except (TypeError, ValueError):
            return None, "Invalid rating"
    if "description" in data:
        out["description"] = str(data["description"])[:2000]
    if "colors" in data:
        c = data["colors"]
        if not (isinstance(c, list) and 1 <= len(c) <= 4 and all(isinstance(x, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", x) for x in c)):
            return None, "colors must be a list of #rrggbb values"
        out["colors"] = json.dumps(c)
    if "image" in data:
        img = str(data["image"])
        if img and not re.fullmatch(r"/uploads/[\w.-]+", img):
            return None, "Invalid image"
        out["image"] = img
    if "active" in data:
        out["active"] = 1 if data["active"] else 0
    return out, None


# ---------- auth ----------
@app.post("/api/auth/register")
def register():
    d = body()
    name, email, pw = str(d.get("name", "")).strip(), str(d.get("email", "")).strip().lower(), str(d.get("password", ""))
    if not name or len(name) > 100:
        return err("Name is required")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return err("Valid email is required")
    if len(pw) < 8:
        return err("Password must be at least 8 characters")
    try:
        cur = db().execute(
            "INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",
            (name, email, generate_password_hash(pw), time.time()),
        )
    except sqlite3.IntegrityError:
        return err("Email already registered", 409)
    u = db().execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(token=new_session(u["id"]), user=user_json(u)), 201


@app.post("/api/auth/login")
def login():
    d = body()
    u = db().execute("SELECT * FROM users WHERE email=?", (str(d.get("email", "")).strip().lower(),)).fetchone()
    if not u or not check_password_hash(u["password_hash"], str(d.get("password", ""))):
        return err("Invalid email or password", 401)
    return jsonify(token=new_session(u["id"]), user=user_json(u))


@app.post("/api/auth/logout")
def logout():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        db().execute("DELETE FROM sessions WHERE token=?", (auth[7:],))
    return jsonify(ok=True)


@app.get("/api/auth/me")
@login_required()
def me():
    return jsonify(user=user_json(g.user))


# ---------- catalogue ----------
@app.get("/api/products")
def list_products():
    rows = db().execute("SELECT * FROM products WHERE active=1 ORDER BY created_at DESC").fetchall()
    return jsonify([product_json(r) for r in rows])


@app.get("/api/products/<int:pid>")
def get_product(pid):
    r = db().execute("SELECT * FROM products WHERE id=? AND active=1", (pid,)).fetchone()
    return jsonify(product_json(r)) if r else err("Not found", 404)


@app.get("/api/pincode/<pin>")
def pincode(pin):
    if not re.fullmatch(r"[1-9]\d{5}", pin):
        return err("Enter a valid 6-digit pincode")
    return jsonify(available=True, days="4-6")


# ---------- wishlist ----------
@app.get("/api/wishlist")
@login_required()
def get_wishlist():
    rows = db().execute("SELECT product_id FROM wishlist WHERE user_id=?", (g.user["id"],)).fetchall()
    return jsonify([r[0] for r in rows])


@app.put("/api/wishlist/<int:pid>")
@login_required()
def add_wishlist(pid):
    if not db().execute("SELECT 1 FROM products WHERE id=? AND active=1", (pid,)).fetchone():
        return err("Not found", 404)
    db().execute("INSERT OR IGNORE INTO wishlist VALUES(?,?)", (g.user["id"], pid))
    return jsonify(ok=True)


@app.delete("/api/wishlist/<int:pid>")
@login_required()
def remove_wishlist(pid):
    db().execute("DELETE FROM wishlist WHERE user_id=? AND product_id=?", (g.user["id"], pid))
    return jsonify(ok=True)


# ---------- orders ----------
def order_json(conn, o):
    d = dict(o)
    d["items"] = [dict(i) for i in conn.execute("SELECT product_id,name,price,qty FROM order_items WHERE order_id=?", (o["id"],))]
    return d


@app.post("/api/orders")
def create_order():
    d = body()
    f = {k: str(d.get(k, "")).strip() for k in ("name", "phone", "email", "address", "city", "pincode")}
    if not all(f.values()) or any(len(v) > 300 for v in f.values()):
        return err("All delivery fields are required")
    if not re.fullmatch(r"[6-9]\d{9}", f["phone"]):
        return err("Invalid mobile number")
    if not re.fullmatch(r"[1-9]\d{5}", f["pincode"]):
        return err("Invalid pincode")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", f["email"]):
        return err("Invalid email")
    pay = d.get("payment_method")
    if pay not in PAY_METHODS:
        return err("Invalid payment method")
    items = d.get("items")
    if not isinstance(items, list) or not items or len(items) > 50:
        return err("Cart is empty")

    qtys = {}
    for it in items:
        try:
            pid, q = int(it["id"]), int(it["qty"])
        except (KeyError, TypeError, ValueError):
            return err("Invalid cart item")
        if q < 1 or q > 20:
            return err("Invalid quantity")
        qtys[pid] = qtys.get(pid, 0) + q

    u = current_user()
    conn = db()
    conn.execute("BEGIN IMMEDIATE")
    try:
        lines, subtotal = [], 0
        for pid, q in qtys.items():
            p = conn.execute("SELECT * FROM products WHERE id=? AND active=1", (pid,)).fetchone()
            if not p:
                raise ValueError("A product in your cart is no longer available")
            if p["stock"] < q:
                raise ValueError(f"Only {p['stock']} left of {p['name']}")
            conn.execute("UPDATE products SET stock=stock-? WHERE id=?", (q, pid))
            lines.append((pid, p["name"], p["price"], q))
            subtotal += p["price"] * q
        shipping = 0 if subtotal >= FREE_SHIP else SHIP_FEE
        oid = "SS" + uuid.uuid4().hex[:8].upper()
        conn.execute(
            "INSERT INTO orders(id,user_id,name,phone,email,address,city,pincode,payment_method,payment_status,subtotal,shipping,total,created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (oid, u["id"] if u else None, f["name"], f["phone"], f["email"], f["address"], f["city"], f["pincode"],
             pay, "Pending", subtotal, shipping, subtotal + shipping, time.time()),
        )
        conn.executemany("INSERT INTO order_items(order_id,product_id,name,price,qty) VALUES(?,?,?,?,?)", [(oid, *l) for l in lines])
        conn.execute("COMMIT")
    except ValueError as e:
        conn.execute("ROLLBACK")
        return err(str(e), 409)
    except Exception:
        conn.execute("ROLLBACK")
        raise
    o = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    return jsonify(order_json(conn, o)), 201


@app.get("/api/orders")
@login_required()
def my_orders():
    rows = db().execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", (g.user["id"],)).fetchall()
    return jsonify([order_json(db(), o) for o in rows])


# ---------- admin ----------
@app.get("/api/admin/stats")
@login_required(admin=True)
def stats():
    c = db()
    return jsonify(
        orders=c.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        revenue=c.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status!='Cancelled'").fetchone()[0],
        products=c.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0],
        lowStock=c.execute("SELECT COUNT(*) FROM products WHERE active=1 AND stock<=3").fetchone()[0],
    )


@app.get("/api/admin/products")
@login_required(admin=True)
def admin_products():
    return jsonify([{**product_json(r), "active": r["active"]} for r in db().execute("SELECT * FROM products ORDER BY created_at DESC")])


@app.post("/api/admin/products")
@login_required(admin=True)
def admin_create_product():
    data, e = clean_product(body())
    if e:
        return err(e)
    data.setdefault("colors", '["#f4c2d0","#f3d9a4"]')
    data["created_at"] = time.time()
    cols = ",".join(data)
    cur = db().execute(f"INSERT INTO products({cols}) VALUES({','.join('?' * len(data))})", list(data.values()))
    r = db().execute("SELECT * FROM products WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(product_json(r)), 201


@app.put("/api/admin/products/<int:pid>")
@login_required(admin=True)
def admin_update_product(pid):
    data, e = clean_product(body(), partial=True)
    if e:
        return err(e)
    if not data:
        return err("Nothing to update")
    cur = db().execute(f"UPDATE products SET {','.join(k + '=?' for k in data)} WHERE id=?", [*data.values(), pid])
    if not cur.rowcount:
        return err("Not found", 404)
    return jsonify(product_json(db().execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()))


@app.delete("/api/admin/products/<int:pid>")
@login_required(admin=True)
def admin_delete_product(pid):
    # Soft delete keeps past orders intact
    cur = db().execute("UPDATE products SET active=0 WHERE id=?", (pid,))
    return jsonify(ok=True) if cur.rowcount else err("Not found", 404)


@app.post("/api/admin/upload")
@login_required(admin=True)
def upload():
    f = request.files.get("file")
    if not f:
        return err("No file")
    head = f.stream.read(12)
    f.stream.seek(0)
    if head.startswith(b"\xff\xd8\xff"):
        ext = "jpg"
    elif head.startswith(b"\x89PNG\r\n\x1a\n"):
        ext = "png"
    elif head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        ext = "webp"
    else:
        return err("Only JPG, PNG or WEBP images are allowed")
    name = f"{uuid.uuid4().hex}.{ext}"
    f.save(UPLOADS / name)
    return jsonify(url=f"/uploads/{name}"), 201


@app.get("/api/admin/orders")
@login_required(admin=True)
def admin_orders():
    rows = db().execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    return jsonify([order_json(db(), o) for o in rows])


@app.patch("/api/admin/orders/<oid>")
@login_required(admin=True)
def admin_order_status(oid):
    d = body()
    conn = db()
    o = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not o:
        return err("Not found", 404)
    updates = {}
    if "status" in d:
        if d["status"] not in ORDER_STATUSES:
            return err("Invalid status")
        updates["status"] = d["status"]
    if d.get("payment_status") in ("Pending", "Paid", "Refunded"):
        updates["payment_status"] = d["payment_status"]
    if not updates:
        return err("Nothing to update")
    conn.execute("BEGIN IMMEDIATE")
    conn.execute(f"UPDATE orders SET {','.join(k + '=?' for k in updates)} WHERE id=?", [*updates.values(), oid])
    # Cancelling returns stock exactly once
    if updates.get("status") == "Cancelled" and o["status"] != "Cancelled":
        conn.execute(
            "UPDATE products SET stock=stock+(SELECT qty FROM order_items WHERE order_id=? AND product_id=products.id)"
            " WHERE id IN (SELECT product_id FROM order_items WHERE order_id=?)", (oid, oid))
    conn.execute("COMMIT")
    return jsonify(order_json(conn, conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()))


# ---------- static ----------
@app.get("/uploads/<path:name>")
def serve_upload(name):
    return send_from_directory(UPLOADS, name)


@app.get("/")
def index():
    return send_from_directory(BASE / "public", "index.html")


@app.get("/<path:name>")
def static_files(name):
    if name.startswith("api/"):
        return err("Not found", 404)
    return send_from_directory(BASE / "public", name)


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5050)))
