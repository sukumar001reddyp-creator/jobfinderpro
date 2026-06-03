from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "jobfinder_secret"


# Create Database
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        jobrole TEXT,
        location TEXT,
        experience TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return "Passwords do not match"

        jobrole = request.form["jobrole"]
        location = request.form["location"]
        experience = request.form["experience"]

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO users
                (name,email,password,jobrole,location,experience)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    name,
                    email,
                    password,
                    jobrole,
                    location,
                    experience
                )
            )

            conn.commit()

        except sqlite3.IntegrityError:
            conn.close()
            return "Email already exists"

        conn.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE email=? AND password=?
            """,
            (email, password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:
            session["user"] = email
            return redirect("/dashboard")

        return "Invalid Login"

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name,email,jobrole,location,experience
        FROM users
        WHERE email=?
        """,
        (session["user"],)
    )

    user = cursor.fetchone()

    conn.close()

    if not user:
        return "User not found"

    return render_template("dashboard.html", user=user)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
