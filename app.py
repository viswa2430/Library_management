from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
import mysql.connector
from datetime import date
from config import db_config

app = Flask(__name__)
app.secret_key = "my_super_secret_1234"
bcrypt = Bcrypt(app)

# ---------- Database Connection ----------


def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

# ---------- Routes ----------


@app.route("/")
def home():
    return redirect(url_for("login"))

# Register


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = bcrypt.generate_password_hash(
            request.form["password"]).decode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, password)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Registration successful!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# Login


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and bcrypt.check_password_hash(user['password'], password):
            session["loggedin"] = True
            session["id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "danger")

    return render_template("login.html")

# Dashboard


@app.route("/dashboard")
def dashboard():
    if "loggedin" in session:
        return render_template("dashboard.html",
                               username=session["username"],
                               role=session["role"])
    return redirect(url_for("login"))

# Add Book


@app.route("/add_book", methods=["GET", "POST"])
def add_book():
    if "loggedin" in session and session["role"] == "admin":
        if request.method == "POST":
            title = request.form["title"]
            author = request.form["author"]
            quantity = int(request.form["quantity"])

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO books (title, author, quantity) VALUES (%s, %s, %s)",
                (title, author, quantity)
            )
            conn.commit()
            cursor.close()
            conn.close()

            flash("Book added successfully!", "success")
            return redirect(url_for("view_books"))

        return render_template("add_book.html")

    flash("Access denied! Only admins can add books.", "danger")
    return redirect(url_for("dashboard"))

# View Books


@app.route("/view_books")
def view_books():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    # All books
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()

    # Borrowed books for logged-in user
    cursor.execute("""
        SELECT t.id, b.title, b.author, t.borrow_date, t.status, t.book_id
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        WHERE t.user_id = %s
    """, (session["id"],))
    borrowed = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("view_books.html",
                           books=books,
                           borrowed=borrowed,
                           role=session.get("role"))

# Borrow Book


@app.route("/borrow/<int:book_id>")
def borrow(book_id):
    if "loggedin" in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM books WHERE id=%s", (book_id,))
        book = cursor.fetchone()

        if book and book['quantity'] > 0:
            cursor.execute(
                "INSERT INTO transactions (user_id, book_id, borrow_date, status) VALUES (%s, %s, %s, %s)",
                (session["id"], book_id, date.today(), "borrowed")
            )
            cursor.execute(
                "UPDATE books SET quantity = quantity - 1 WHERE id=%s", (book_id,)
            )
            conn.commit()
            flash("Book borrowed successfully!", "success")
        else:
            flash("Book not available", "danger")

        cursor.close()
        conn.close()

    return redirect(url_for("view_books"))

# Return Book


@app.route("/return/<int:transaction_id>")
def return_book(transaction_id):
    if "loggedin" in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM transactions WHERE id=%s",
                       (transaction_id,))
        transaction = cursor.fetchone()

        if transaction and transaction['status'] == 'borrowed':
            cursor.execute(
                "UPDATE transactions SET status=%s, return_date=%s WHERE id=%s",
                ("returned", date.today(), transaction_id)
            )
            cursor.execute(
                "UPDATE books SET quantity = quantity + 1 WHERE id=%s",
                (transaction['book_id'],)
            )
            conn.commit()
            flash("Book returned successfully!", "success")

        cursor.close()
        conn.close()

    return redirect(url_for("view_books"))

# Logout


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))


# ---------- Run App ----------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
