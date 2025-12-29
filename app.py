from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'deefefefrgr15345ii')

# ---------- DB ----------

def get_db():
    conn = sqlite3.connect("magazin.db")
    conn.row_factory = sqlite3.Row
    return conn

def get_catalog():
    conn = get_db()
    categories = conn.execute("SELECT id, name FROM categories").fetchall()
    result = []

    for c in categories:
        subs = conn.execute(
            "SELECT id, name FROM subcategories WHERE category_id=?",
            (c["id"],)
        ).fetchall()

        result.append({
            "id": c["id"],
            "name": c["name"],
            "subcategories": subs
        })

    conn.close()
    return result

def get_popular_products():
    conn = get_db()
    products = conn.execute(
        "SELECT id, name, price, image FROM products WHERE popular=1 LIMIT 6"
    ).fetchall()
    conn.close()
    return products

# ---------- CART ----------

def get_cart():
    return session.get("cart", {})

@app.route("/add_to_cart/<int:id>")
def add_to_cart(id):
    qty = int(request.args.get("qty", 1))
    cart = get_cart()
    cart[str(id)] = cart.get(str(id), 0) + qty
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/cart", methods=["GET", "POST"])
def cart():
    cart = get_cart()
    if not cart:
        return render_template("cart.html", products=[], total=0)

    conn = get_db()
    ids = tuple(map(int, cart.keys()))
    q = f"SELECT * FROM products WHERE id IN ({','.join('?'*len(ids))})"
    products = conn.execute(q, ids).fetchall()
    conn.close()

    items = []
    total = 0

    for p in products:
        qty = cart[str(p["id"])]
        s = qty * p["price"]
        total += s
        items.append({**p, "qty": qty, "sum": s})

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        address = request.form["address"]
        comment = request.form["comment"]

        conn = get_db()
        
        order_id = conn.execute(
            "INSERT INTO orders (name, phone, address, comment, total_price) VALUES(?,?,?,?,?)",
            (name, phone, address, comment, total)
        ).lastrowid
        for item in items:
            conn.execute("INSERT INTO order_products (order_id, product_id, quantity) VALUES(?,?,?)",
                         (order_id, item["id"], item["qty"])
                         )
        conn.commit()
        conn.close()
        session['cart'] = {}
        return redirect("/order_confirmation")

    return render_template("cart.html", products=items, total=total)

@app.route("/clear_cart")
def clear_cart():
    session["cart"] = {}
    return redirect(url_for("cart"))

# ---------- ROUTES ----------

@app.route("/")
def index():
    conn = get_db()
    comments = conn.execute(
        """SELECT c.text, c.author, p.name AS product
           FROM comments c
           JOIN products p ON p.id=c.product_id
           ORDER BY c.created_at DESC
           LIMIT 5"""
    ).fetchall()
    conn.close()

    return render_template(
        "index.html",
        popular=get_popular_products(),
        comments=comments
    )

@app.route("/catalog")
def catalog():
    return render_template(
        "catalog.html",
        categories=get_catalog(),
        products=None,
        popular=get_popular_products(),
        current_subcategory=None
    )

@app.route("/subcategory/<int:id>")
def subcategory(id):
    conn = get_db()
    products = conn.execute(
        "SELECT * FROM products WHERE subcategory_id=?",
        (id,)
    ).fetchall()
    conn.close()

    return render_template(
        "catalog.html",
        categories=get_catalog(),
        products=products,
        popular=None,
        current_subcategory=id
    )

@app.route("/product/<int:id>")
def product(id):
    conn = get_db()
    product = conn.execute(
        "SELECT * FROM products WHERE id=?",
        (id,)
    ).fetchone()

    comments = conn.execute(
        "SELECT * FROM comments WHERE product_id=? ORDER BY created_at DESC",
        (id,)
    ).fetchall()

    conn.close()

    return render_template(
        "product.html",
        product=product,
        comments=comments
    )

@app.route("/add_comment/<int:id>", methods=["POST"])
def add_comment(id):
    author = request.form["author"]
    text = request.form["text"]

    conn = get_db()
    conn.execute(
        "INSERT INTO comments (product_id, author, text) VALUES (?, ?, ?)",
        (id, author, text)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("product", id=id))

@app.route("/contacts")
def contacts():
    return render_template("contacts.html")

@app.route("/order_confirmation")
def order_confirmation():
    return render_template("order_confirmation.html")

@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return redirect(url_for("catalog"))

    conn = get_db()
    products = conn.execute(
        "SELECT * FROM products WHERE name LIKE ? COLLATE NOCASE",
        ["%"+q+"%"]
    ).fetchall() or []
    conn.close()

    return render_template("catalog.html", products=products)
# ---------- RUN ----------

if __name__ == "__main__":
    app.run(debug=True)