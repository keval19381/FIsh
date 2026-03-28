import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fish-delivery-secret")

DB_PATH = os.path.join(os.path.dirname(__file__), "fish_delivery.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_address TEXT NOT NULL,
            fish_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fish_id) REFERENCES fish(id)
        )
    """)
    conn.commit()
    conn.close()


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
                fish = conn.execute("SELECT * FROM fish WHERE id = ? AND available = 1", (fish_id,)).fetchone()
                if not fish:
                    flash("Selected fish is not available.", "error")
                else:
                    conn.execute(
                        "INSERT INTO orders (customer_name, customer_address, fish_id, quantity) VALUES (?, ?, ?, ?)",
                        (customer_name, customer_address, fish_id, qty)
                    )
                    conn.commit()
                    flash(f"Order placed! {qty} x {fish['name']} will be delivered to {customer_address}.", "success")
                    return redirect(url_for("customer"))
                conn.close()
            except ValueError:
                flash("Quantity must be a positive number.", "error")

    conn = get_db()
    fish_list = conn.execute("SELECT * FROM fish WHERE available = 1 ORDER BY name").fetchall()
    conn.close()
    return render_template("customer.html", fish_list=fish_list)


@app.route("/delivery")
def delivery():
    conn = get_db()
    orders = conn.execute("""
        SELECT orders.id, orders.customer_name, orders.customer_address,
               orders.quantity, orders.status, orders.created_at,
               fish.name as fish_name, fish.price as fish_price
        FROM orders
        JOIN fish ON orders.fish_id = fish.id
        ORDER BY orders.created_at DESC
    """).fetchall()
    conn.close()
    return render_template("delivery.html", orders=orders)


@app.route("/delivery/update/<int:order_id>", methods=["POST"])
def update_order_status(order_id):
    new_status = request.form.get("status", "pending")
    valid_statuses = ["pending", "preparing", "out_for_delivery", "delivered", "cancelled"]
    if new_status in valid_statuses:
        conn = get_db()
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        conn.commit()
        conn.close()
        flash("Order status updated.", "success")
    return redirect(url_for("delivery"))


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
