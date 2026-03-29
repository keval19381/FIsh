import os
import hashlib
import sqlite3
import uuid
from functools import wraps
from datetime import datetime
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fishdelivery-secret-key-2024")

DB_PATH = os.path.join(os.path.dirname(__file__), "fish_delivery.db")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def gen_order_number():
    return "ORD-" + uuid.uuid4().hex[:8].upper()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('seller','customer','delivery','admin')),
            city TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS fish (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            image_path TEXT DEFAULT '',
            description TEXT DEFAULT '',
            available INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (seller_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT NOT NULL UNIQUE,
            customer_id INTEGER NOT NULL,
            fish_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            assigned_to INTEGER,
            delivery_address TEXT NOT NULL,
            delivery_city TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES users(id),
            FOREIGN KEY (fish_id) REFERENCES fish(id),
            FOREIGN KEY (assigned_to) REFERENCES users(id)
        )
    """)

    c.execute(
        """
        INSERT OR IGNORE INTO users (name, email, password_hash, role, city)
        VALUES ('Admin', 'admin@fish.com', ?, 'admin', 'Mumbai')
    """,
        (hash_password("admin123"),),
    )

    conn.commit()
    conn.close()


# ── Decorators ─────────────────────────────────────────────────────────────


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login"))
            if session.get("user_role") not in roles:
                flash("You don't have permission to access this page.", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)

        return decorated

    return decorator


# ── Home ────────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    conn = get_db()
    fish_count = conn.execute("SELECT COUNT(*) FROM fish WHERE available=1").fetchone()[
        0
    ]
    order_count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    seller_count = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role='seller'"
    ).fetchone()[0]
    conn.close()
    return render_template(
        "index.html",
        fish_count=fish_count,
        order_count=order_count,
        seller_count=seller_count,
    )


# ── Auth ─────────────────────────────────────────────────────────────────────


@app.route("/auth/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("role_home"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        if not email or not password:
            flash("Email and password are required.", "error")
        else:
            conn = get_db()
            user = conn.execute(
                "SELECT * FROM users WHERE email=? AND password_hash=?",
                (email, hash_password(password)),
            ).fetchone()
            conn.close()
            if user:
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["user_role"] = user["role"]
                session["user_email"] = user["email"]
                flash(f"Welcome back, {user['name']}! 👋", "success")
                return redirect(url_for("role_home"))
            flash("Invalid email or password.", "error")
    return render_template("auth/login.html")


@app.route("/auth/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("role_home"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "customer")
        city = request.form.get("city", "").strip()

        if not name or not email or not password:
            flash("Name, email and password are required.", "error")
        elif role not in ("seller", "customer", "delivery"):
            flash("Invalid role selected.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        else:
            try:
                conn = get_db()
                conn.execute(
                    "INSERT INTO users (name, email, password_hash, role, city) VALUES (?,?,?,?,?)",
                    (name, email, hash_password(password), role, city),
                )
                conn.commit()
                conn.close()
                flash("Account created successfully! Please log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Email already registered. Try logging in.", "error")
    return render_template("auth/register.html")


@app.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


@app.route("/role-home")
@login_required
def role_home():
    role = session.get("user_role")
    if role == "seller":
        return redirect(url_for("seller_dashboard"))
    elif role == "customer":
        return redirect(url_for("customer_browse"))
    elif role in ("delivery", "admin"):
        return redirect(
            url_for("delivery_admin" if role == "admin" else "delivery_orders")
        )
    return redirect(url_for("index"))


# ── Seller ───────────────────────────────────────────────────────────────────


@app.route("/seller")
@role_required("seller", "admin")
def seller_dashboard():
    conn = get_db()
    fish_list = (
        conn.execute(
            "SELECT * FROM fish WHERE seller_id=? ORDER BY id DESC",
            (session["user_id"],),
        ).fetchall()
        if session["user_role"] == "seller"
        else conn.execute(
            "SELECT f.*, u.name as seller_name FROM fish f JOIN users u ON f.seller_id=u.id ORDER BY f.id DESC"
        ).fetchall()
    )

    total_orders = conn.execute(
        "SELECT COUNT(*) FROM orders o JOIN fish f ON o.fish_id=f.id WHERE f.seller_id=?",
        (session["user_id"],),
    ).fetchone()[0]
    revenue = conn.execute(
        "SELECT COALESCE(SUM(o.total_price),0) FROM orders o JOIN fish f ON o.fish_id=f.id WHERE f.seller_id=? AND o.status='delivered'",
        (session["user_id"],),
    ).fetchone()[0]
    conn.close()
    return render_template(
        "seller/dashboard.html",
        fish_list=fish_list,
        total_orders=total_orders,
        revenue=revenue,
    )


@app.route("/seller/add", methods=["GET", "POST"])
@role_required("seller", "admin")
def seller_add_fish():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price", "").strip()
        description = request.form.get("description", "").strip()
        image_path = ""

        if not name or not price:
            flash("Fish name and price are required.", "error")
            return render_template("seller/add_fish.html")

        try:
            price_val = float(price)
            if price_val <= 0:
                raise ValueError
        except ValueError:
            flash("Price must be a positive number.", "error")
            return render_template("seller/add_fish.html")

        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                image_path = f"uploads/{filename}"

        conn = get_db()
        conn.execute(
            "INSERT INTO fish (seller_id, name, price, image_path, description) VALUES (?,?,?,?,?)",
            (session["user_id"], name, price_val, image_path, description),
        )
        conn.commit()
        conn.close()
        flash(f'"{name}" added successfully! 🐟', "success")
        return redirect(url_for("seller_dashboard"))

    return render_template("seller/add_fish.html")


@app.route("/seller/fish/toggle/<int:fish_id>", methods=["POST"])
@role_required("seller", "admin")
def seller_toggle(fish_id):
    conn = get_db()
    fish = conn.execute("SELECT * FROM fish WHERE id=?", (fish_id,)).fetchone()
    if fish:
        conn.execute(
            "UPDATE fish SET available=? WHERE id=?",
            (0 if fish["available"] else 1, fish_id),
        )
        conn.commit()
    conn.close()
    flash("Availability updated.", "success")
    return redirect(url_for("seller_dashboard"))


@app.route("/seller/fish/delete/<int:fish_id>", methods=["POST"])
@role_required("seller", "admin")
def seller_delete(fish_id):
    conn = get_db()
    fish = conn.execute("SELECT * FROM fish WHERE id=?", (fish_id,)).fetchone()
    if fish and fish["image_path"]:
        img = os.path.join(os.path.dirname(__file__), "static", fish["image_path"])
        if os.path.exists(img):
            os.remove(img)
    conn.execute("DELETE FROM fish WHERE id=?", (fish_id,))
    conn.commit()
    conn.close()
    flash("Fish removed.", "success")
    return redirect(url_for("seller_dashboard"))


# ── Customer ─────────────────────────────────────────────────────────────────


@app.route("/customer")
@role_required("customer", "admin")
def customer_browse():
    query = request.args.get("q", "").strip()
    conn = get_db()
    if query:
        fish_list = conn.execute(
            "SELECT * FROM fish WHERE available=1 AND name LIKE ? ORDER BY name",
            (f"%{query}%",),
        ).fetchall()
    else:
        fish_list = conn.execute(
            "SELECT * FROM fish WHERE available=1 ORDER BY name"
        ).fetchall()
    conn.close()
    return render_template("customer/browse.html", fish_list=fish_list, query=query)


@app.route("/customer/order/<int:fish_id>", methods=["GET", "POST"])
@role_required("customer", "admin")
def customer_order(fish_id):
    conn = get_db()
    fish = conn.execute(
        "SELECT * FROM fish WHERE id=? AND available=1", (fish_id,)
    ).fetchone()
    if not fish:
        flash("This fish is no longer available.", "error")
        conn.close()
        return redirect(url_for("customer_browse"))

    if request.method == "POST":
        qty_str = request.form.get("quantity", "1").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()

        try:
            qty = float(qty_str)
            if qty <= 0:
                raise ValueError
        except ValueError:
            flash("Quantity must be a positive number.", "error")
            return render_template("customer/order.html", fish=fish)

        if not address:
            flash("Delivery address is required.", "error")
            return render_template("customer/order.html", fish=fish)

        total = round(fish["price"] * qty, 2)
        order_num = gen_order_number()
        conn.execute(
            "INSERT INTO orders (order_number, customer_id, fish_id, quantity, total_price, delivery_address, delivery_city) VALUES (?,?,?,?,?,?,?)",
            (order_num, session["user_id"], fish_id, qty, total, address, city),
        )
        conn.commit()
        order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        flash(f"Order placed successfully! Order ID: {order_num}", "success")
        return redirect(url_for("customer_confirm", order_id=order_id))

    conn.close()
    return render_template("customer/order.html", fish=fish)


@app.route("/customer/confirm/<int:order_id>")
@role_required("customer", "admin")
def customer_confirm(order_id):
    conn = get_db()
    order = conn.execute(
        """
        SELECT o.*, f.name as fish_name, f.price as fish_price, f.image_path
        FROM orders o JOIN fish f ON o.fish_id=f.id
        WHERE o.id=? AND o.customer_id=?
    """,
        (order_id, session["user_id"]),
    ).fetchone()
    conn.close()
    if not order:
        return redirect(url_for("customer_browse"))
    return render_template("customer/confirm.html", order=order)


@app.route("/customer/orders")
@role_required("customer", "admin")
def customer_orders():
    conn = get_db()
    orders = conn.execute(
        """
        SELECT o.*, f.name as fish_name, f.image_path,
               u.name as partner_name
        FROM orders o
        JOIN fish f ON o.fish_id=f.id
        LEFT JOIN users u ON o.assigned_to=u.id
        WHERE o.customer_id=?
        ORDER BY o.created_at DESC
    """,
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("customer/orders.html", orders=orders)


# ── Delivery ─────────────────────────────────────────────────────────────────


@app.route("/delivery")
@login_required
def delivery_home():
    role = session.get("user_role")
    if role == "admin":
        return redirect(url_for("delivery_admin"))
    elif role == "delivery":
        return redirect(url_for("delivery_orders"))
    flash("Delivery partner or admin access required.", "error")
    return redirect(url_for("index"))


@app.route("/delivery/orders")
@role_required("delivery", "admin")
def delivery_orders():
    status_filter = request.args.get("status", "all")
    conn = get_db()
    base_q = """
        SELECT o.*, f.name as fish_name, f.price as fish_price,
               u.name as customer_name, u.city as customer_city
        FROM orders o
        JOIN fish f ON o.fish_id=f.id
        JOIN users u ON o.customer_id=u.id
        WHERE o.assigned_to=?
    """
    if status_filter != "all":
        orders = conn.execute(
            base_q + " AND o.status=? ORDER BY o.created_at DESC",
            (session["user_id"], status_filter),
        ).fetchall()
    else:
        orders = conn.execute(
            base_q + " ORDER BY o.created_at DESC", (session["user_id"],)
        ).fetchall()
    conn.close()
    return render_template(
        "delivery/my_orders.html", orders=orders, status_filter=status_filter
    )


@app.route("/delivery/orders/update/<int:order_id>", methods=["POST"])
@role_required("delivery", "admin")
def delivery_update(order_id):
    new_status = request.form.get("status")
    valid = ["pending", "preparing", "out_for_delivery", "delivered", "cancelled"]
    if new_status in valid:
        conn = get_db()
        conn.execute(
            "UPDATE orders SET status=? WHERE id=? AND assigned_to=?",
            (new_status, order_id, session["user_id"]),
        )
        conn.commit()
        conn.close()
        flash("Order status updated.", "success")
    return redirect(url_for("delivery_orders"))


@app.route("/delivery/admin")
@role_required("admin")
def delivery_admin():
    status_filter = request.args.get("status", "all")
    conn = get_db()
    base_q = """
        SELECT o.*, f.name as fish_name, f.price as fish_price,
               uc.name as customer_name,
               ud.name as partner_name
        FROM orders o
        JOIN fish f ON o.fish_id=f.id
        JOIN users uc ON o.customer_id=uc.id
        LEFT JOIN users ud ON o.assigned_to=ud.id
    """
    if status_filter != "all":
        orders = conn.execute(
            base_q + " WHERE o.status=? ORDER BY o.created_at DESC", (status_filter,)
        ).fetchall()
    else:
        orders = conn.execute(base_q + " ORDER BY o.created_at DESC").fetchall()

    partners = conn.execute(
        "SELECT id, name, city FROM users WHERE role IN ('delivery','admin') ORDER BY name"
    ).fetchall()

    stats = {
        "total": conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "pending": conn.execute(
            "SELECT COUNT(*) FROM orders WHERE status='pending'"
        ).fetchone()[0],
        "active": conn.execute(
            "SELECT COUNT(*) FROM orders WHERE status IN ('preparing','out_for_delivery')"
        ).fetchone()[0],
        "delivered": conn.execute(
            "SELECT COUNT(*) FROM orders WHERE status='delivered'"
        ).fetchone()[0],
        "unassigned": conn.execute(
            "SELECT COUNT(*) FROM orders WHERE assigned_to IS NULL"
        ).fetchone()[0],
        "revenue": conn.execute(
            "SELECT COALESCE(SUM(total_price),0) FROM orders WHERE status='delivered'"
        ).fetchone()[0],
    }
    conn.close()
    return render_template(
        "delivery/admin.html",
        orders=orders,
        partners=partners,
        stats=stats,
        status_filter=status_filter,
    )


@app.route("/delivery/admin/assign/<int:order_id>", methods=["POST"])
@role_required("admin")
def delivery_assign(order_id):
    partner_id = request.form.get("partner_id", "").strip()
    conn = get_db()
    if partner_id:
        conn.execute(
            "UPDATE orders SET assigned_to=? WHERE id=?", (int(partner_id), order_id)
        )
        p = conn.execute("SELECT name FROM users WHERE id=?", (partner_id,)).fetchone()
        flash(f"Assigned to {p['name']}.", "success")
    else:
        conn.execute("UPDATE orders SET assigned_to=NULL WHERE id=?", (order_id,))
        flash("Order unassigned.", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("delivery_admin"))


@app.route("/delivery/admin/status/<int:order_id>", methods=["POST"])
@role_required("admin")
def delivery_admin_status(order_id):
    new_status = request.form.get("status")
    valid = ["pending", "preparing", "out_for_delivery", "delivered", "cancelled"]
    if new_status in valid:
        conn = get_db()
        conn.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
        conn.commit()
        conn.close()
        flash("Status updated.", "success")
    return redirect(url_for("delivery_admin"))


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
