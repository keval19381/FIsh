import os
import hashlib
import sqlite3
from flask import (Flask, render_template, request, redirect,
                   url_for, flash, session)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fish-delivery-super-secret-2024")

DB_PATH = os.path.join(os.path.dirname(__file__), "fish_delivery.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS fish (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            available INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS delivery_partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            phone TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_address TEXT NOT NULL,
            fish_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            status TEXT DEFAULT 'pending',
            assigned_to INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fish_id) REFERENCES fish(id),
            FOREIGN KEY (assigned_to) REFERENCES delivery_partners(id)
        )
    """)

    c.execute("""
        INSERT OR IGNORE INTO delivery_partners (name, username, password_hash, phone, is_admin)
        VALUES ('Admin', 'admin', ?, '000-0000', 1)
    """, (hash_password("admin123"),))

    conn.commit()
    conn.close()


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "partner_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("delivery_login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "partner_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("delivery_login"))
        if not session.get("is_admin"):
            flash("Admin access required.", "error")
            return redirect(url_for("my_orders"))
        return f(*args, **kwargs)
    return decorated


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/seller", methods=["GET", "POST"])
def seller():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price", "").strip()
        if not name or not price:
            flash("Please fill in all fields.", "error")
        else:
            try:
                price_val = float(price)
                if price_val <= 0:
                    raise ValueError
                conn = get_db()
                conn.execute("INSERT INTO fish (name, price) VALUES (?, ?)", (name, price_val))
                conn.commit()
                conn.close()
                flash(f'"{name}" added successfully!', "success")
                return redirect(url_for("seller"))
            except ValueError:
                flash("Price must be a positive number.", "error")

    conn = get_db()
    fish_list = conn.execute("SELECT * FROM fish ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("seller.html", fish_list=fish_list)


@app.route("/seller/toggle/<int:fish_id>", methods=["POST"])
def toggle_availability(fish_id):
    conn = get_db()
    fish = conn.execute("SELECT * FROM fish WHERE id = ?", (fish_id,)).fetchone()
    if fish:
        new_status = 0 if fish["available"] else 1
        conn.execute("UPDATE fish SET available = ? WHERE id = ?", (new_status, fish_id))
        conn.commit()
        flash("Availability updated.", "success")
    conn.close()
    return redirect(url_for("seller"))


@app.route("/seller/delete/<int:fish_id>", methods=["POST"])
def delete_fish(fish_id):
    conn = get_db()
    conn.execute("DELETE FROM fish WHERE id = ?", (fish_id,))
    conn.commit()
    conn.close()
    flash("Fish removed.", "success")
    return redirect(url_for("seller"))


@app.route("/customer", methods=["GET", "POST"])
def customer():
    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        customer_address = request.form.get("customer_address", "").strip()
        fish_id = request.form.get("fish_id", "").strip()
        quantity = request.form.get("quantity", "1").strip()

        if not customer_name or not customer_address or not fish_id:
            flash("Please fill in all fields.", "error")
        else:
            try:
                qty = int(quantity)
                if qty <= 0:
                    raise ValueError
                conn = get_db()
                fish = conn.execute(
                    "SELECT * FROM fish WHERE id = ? AND available = 1", (fish_id,)
                ).fetchone()
                if not fish:
                    flash("Selected fish is not available.", "error")
                    conn.close()
                else:
                    conn.execute(
                        "INSERT INTO orders (customer_name, customer_address, fish_id, quantity) VALUES (?, ?, ?, ?)",
                        (customer_name, customer_address, fish_id, qty)
                    )
                    conn.commit()
                    conn.close()
                    flash(
                        f"Order placed! {qty} kg of {fish['name']} will be delivered to {customer_address}.",
                        "success"
                    )
                    return redirect(url_for("customer"))
            except ValueError:
                flash("Quantity must be a positive number.", "error")

    conn = get_db()
    fish_list = conn.execute("SELECT * FROM fish WHERE available = 1 ORDER BY name").fetchall()
    conn.close()
    return render_template("customer.html", fish_list=fish_list)


@app.route("/delivery/login", methods=["GET", "POST"])
def delivery_login():
    if "partner_id" in session:
        return redirect(url_for("my_orders"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            flash("Please enter username and password.", "error")
        else:
            conn = get_db()
            partner = conn.execute(
                "SELECT * FROM delivery_partners WHERE username = ? AND password_hash = ?",
                (username, hash_password(password))
            ).fetchone()
            conn.close()
            if partner:
                session["partner_id"] = partner["id"]
                session["partner_name"] = partner["name"]
                session["is_admin"] = bool(partner["is_admin"])
                flash(f"Welcome back, {partner['name']}!", "success")
                if partner["is_admin"]:
                    return redirect(url_for("delivery_all"))
                return redirect(url_for("my_orders"))
            else:
                flash("Invalid username or password.", "error")

    return render_template("delivery_login.html")


@app.route("/delivery/register", methods=["GET", "POST"])
def delivery_register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        phone = request.form.get("phone", "").strip()

        if not name or not username or not password:
            flash("Name, username and password are required.", "error")
        else:
            try:
                conn = get_db()
                conn.execute(
                    "INSERT INTO delivery_partners (name, username, password_hash, phone) VALUES (?, ?, ?, ?)",
                    (name, username, hash_password(password), phone)
                )
                conn.commit()
                conn.close()
                flash("Account created! You can now log in.", "success")
                return redirect(url_for("delivery_login"))
            except sqlite3.IntegrityError:
                flash("Username already taken. Choose a different one.", "error")

    return render_template("delivery_register.html")


@app.route("/delivery/logout", methods=["POST"])
def delivery_logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("delivery_login"))


@app.route("/delivery/my-orders")
@login_required
def my_orders():
    conn = get_db()
    orders = conn.execute("""
        SELECT orders.id, orders.customer_name, orders.customer_address,
               orders.quantity, orders.status, orders.created_at,
               fish.name as fish_name, fish.price as fish_price
        FROM orders
        JOIN fish ON orders.fish_id = fish.id
        WHERE orders.assigned_to = ?
        ORDER BY orders.created_at DESC
    """, (session["partner_id"],)).fetchall()
    conn.close()
    return render_template("my_orders.html", orders=orders)


@app.route("/delivery/my-orders/update/<int:order_id>", methods=["POST"])
@login_required
def update_my_order(order_id):
    new_status = request.form.get("status", "pending")
    valid_statuses = ["pending", "preparing", "out_for_delivery", "delivered", "cancelled"]
    if new_status in valid_statuses:
        conn = get_db()
        conn.execute(
            "UPDATE orders SET status = ? WHERE id = ? AND assigned_to = ?",
            (new_status, order_id, session["partner_id"])
        )
        conn.commit()
        conn.close()
        flash("Order status updated.", "success")
    return redirect(url_for("my_orders"))


@app.route("/delivery/all-orders")
@admin_required
def delivery_all():
    conn = get_db()
    orders = conn.execute("""
        SELECT orders.id, orders.customer_name, orders.customer_address,
               orders.quantity, orders.status, orders.created_at,
               fish.name as fish_name, fish.price as fish_price,
               delivery_partners.name as partner_name,
               orders.assigned_to
        FROM orders
        JOIN fish ON orders.fish_id = fish.id
        LEFT JOIN delivery_partners ON orders.assigned_to = delivery_partners.id
        ORDER BY orders.created_at DESC
    """).fetchall()

    partners = conn.execute(
        "SELECT id, name FROM delivery_partners WHERE is_admin = 0 ORDER BY name"
    ).fetchall()
    conn.close()
    return render_template("delivery_all.html", orders=orders, partners=partners)


@app.route("/delivery/assign/<int:order_id>", methods=["POST"])
@admin_required
def assign_order(order_id):
    partner_id = request.form.get("partner_id", "").strip()
    conn = get_db()
    if partner_id:
        conn.execute(
            "UPDATE orders SET assigned_to = ? WHERE id = ?",
            (int(partner_id), order_id)
        )
        partner = conn.execute(
            "SELECT name FROM delivery_partners WHERE id = ?", (partner_id,)
        ).fetchone()
        flash(f"Order assigned to {partner['name']}.", "success")
    else:
        conn.execute("UPDATE orders SET assigned_to = NULL WHERE id = ?", (order_id,))
        flash("Order unassigned.", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("delivery_all"))


@app.route("/delivery/update/<int:order_id>", methods=["POST"])
@admin_required
def update_order_status(order_id):
    new_status = request.form.get("status", "pending")
    valid_statuses = ["pending", "preparing", "out_for_delivery", "delivered", "cancelled"]
    if new_status in valid_statuses:
        conn = get_db()
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        conn.commit()
        conn.close()
        flash("Order status updated.", "success")
    return redirect(url_for("delivery_all"))


@app.route("/delivery")
def delivery():
    return redirect(url_for("delivery_login"))


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
