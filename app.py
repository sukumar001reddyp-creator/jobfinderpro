import threading
from flask import copy_current_request_context
import os
import random
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_mail import Mail, Message
from datetime import timedelta

app = Flask(__name__)

# Render/Local Security Wrapper Settings
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'jobfinder_secret_strongly_hashed_2026')
app.permanent_session_lifetime = timedelta(days=30)

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'jobfinderpro85@gmail.com'
app.config['MAIL_PASSWORD'] = 'eole ihak wvty vumv'

mail = Mail(app)

# ==================== SMART HYBRID DATABASE BLOCK ====================
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if DATABASE_URL:
        # Cloud: PostgreSQL Connection
        url = DATABASE_URL
        if "sslmode" not in url:
            url += "&sslmode=require" if "?" in url else "?sslmode=require"
        conn = psycopg2.connect(url)
        return conn
    else:
        # Local: SQLite Connection
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        DB_PATH = os.path.join(BASE_DIR, "users.db")
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

# Dynamic Placeholder (Postgres కి %s, SQLite కి ?)
P = "%s" if DATABASE_URL else "?"

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DATABASE_URL:
        # Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            email VARCHAR(255) UNIQUE,
            password VARCHAR(255),
            jobrole VARCHAR(255),
            location VARCHAR(255),
            experience VARCHAR(255)
        )
        """)
        # OTP Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            email VARCHAR(255) PRIMARY KEY,
            otp VARCHAR(10),
            verified BOOLEAN DEFAULT FALSE
        )
        """)
    else:
        # SQLite Tables
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
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            email TEXT PRIMARY KEY,
            otp TEXT,
            verified INTEGER DEFAULT 0
        )
        """)
    conn.commit()
    cursor.close()
    conn.close()

try:
    init_db()
except Exception as db_init_err:
    print(f"Database initial runtime notice: {str(db_init_err)}")
# ===========================================================================

@app.context_processor
def inject_user():
    if "user" not in session:
        return dict(logged_user=None)

    conn = get_db_connection()
    if DATABASE_URL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()

    cursor.execute(
        f"SELECT name FROM users WHERE email={P}",
        (session["user"],)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        try:
            return dict(logged_user=user["name"])
        except:
            return dict(logged_user=user[0])

    return dict(logged_user=None)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        jobrole = request.form.get("jobrole", "").strip()
        location = request.form.get("location", "").strip()
        experience = request.form.get("experience", "").strip()

        if not all([name, email, password, jobrole, location, experience]):
            return "All fields are required!"

        if password != confirm_password:
            return "Passwords do not match!"

        conn = get_db_connection()
        cursor = conn.cursor()
        success = False
        error_msg = None

        try:
            cursor.execute(
                f"""
                INSERT INTO users (name, email, password, jobrole, location, experience)
                VALUES ({P}, {P}, {P}, {P}, {P}, {P})
                """,
                (name, email, password, jobrole, location, experience)
            )
            conn.commit()
            success = True
        except Exception as e:
            error_msg = "Email already exists or Database Error occurred."
        finally:
            cursor.close()
            conn.close()

        if success:
            return redirect(url_for("login"))
        return error_msg
    
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor) if DATABASE_URL else conn.cursor()
        cursor.execute(
            f"SELECT * FROM users WHERE email={P} AND password={P}",
            (email, password)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session.permanent = True
            session["user"] = user["email"] if DATABASE_URL else user[2] # Handles sqlite row indexing if tuple
            return redirect(url_for("dashboard"))

        return "Invalid Login Credentials"

    return render_template("login.html") 


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT name, email, jobrole, location, experience FROM users WHERE email={P}",
        (session["user"],)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user is None:
        return "User session expired or not found."

    return render_template("dashboard.html", user=user)


@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    if "user" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        jobrole = request.form["jobrole"]
        location = request.form["location"]
        experience = request.form["experience"]

        cursor.execute(
            f"""
            UPDATE users
            SET name={P}, jobrole={P}, location={P}, experience={P}
            WHERE email={P}
            """,
            (name, jobrole, location, experience, session["user"])
        )
        conn.commit()
        conn.close()
        return redirect("/dashboard")

    cursor.execute(
        f"SELECT name, email, jobrole, location, experience FROM users WHERE email={P}",
        (session["user"],)
    )
    user = cursor.fetchone()
    conn.close()

    return render_template("edit_profile.html", user=user)


@app.route("/search")
def search():
    logged_user = None
    if "user" in session:
        logged_user = session["user"]

    role = request.args.get("role", "").strip()
    location = request.args.get("location", "").strip()
    experience = request.args.get("experience", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) if DATABASE_URL else conn.cursor()

    like_op = "ILIKE" if DATABASE_URL else "LIKE"
    query = "SELECT name, email, jobrole, location, experience FROM users WHERE 1=1"
    params = []

    if role:
        query += f" AND jobrole {like_op} {P}"
        params.append(f"%{role}%")
    if location:
        query += f" AND location {like_op} {P}"
        params.append(f"%{location}%")
    if experience:
        query += f" AND experience = {P}"
        params.append(experience)

    cursor.execute(query, tuple(params))
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        "search.html",
        results=results,
        role=role,
        location=location,
        experience=experience,
        logged_user=logged_user
    )


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor) if DATABASE_URL else conn.cursor()
        cursor.execute(f"SELECT email FROM users WHERE email={P}", (email,))
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            return "Email address not registered! Please crosscheck."

        otp = str(random.randint(100000, 999999))
        
        cursor.execute(f"SELECT email FROM password_resets WHERE email={P}", (email,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute(f"UPDATE password_resets SET otp={P}, verified={P} WHERE email={P}", (otp, False, email))
        else:
            cursor.execute(f"INSERT INTO password_resets (email, otp, verified) VALUES ({P}, {P}, {P})", (email, otp, False))
        
        conn.commit()
        cursor.close()
        conn.close()

        session['reset_email'] = str(email)

        msg = Message(
            "JobFinder Password Reset OTP",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"Hello,\n\nYour JobFinder password reset OTP is: {otp}\n\nTeam JobFinder"
        try:
            mail.send(msg)
            print("MAIL SENT SUCCESSFULLY")
        except Exception as e:
            print("MAIL ERROR:", str(e))
            flash("Unable to send OTP email.", "danger")
            return redirect(url_for('forgot_password'))

        if not DATABASE_URL:
            flash(f"Local test mode active. Your OTP is: {otp}", "info")

        return redirect(url_for('verify_otp'))

    return render_template('forgot_password.html')


@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = session.get('reset_email')
    if not email:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor) if DATABASE_URL else conn.cursor()
        cursor.execute(f"SELECT otp FROM password_resets WHERE email={P}", (email,))
        row = cursor.fetchone()

        db_otp = row['otp'] if DATABASE_URL else row[0]

        if row and str(db_otp).strip() == entered_otp:
            cursor.execute(f"UPDATE password_resets SET verified={P} WHERE email={P}", (1, email))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('reset_password'))
        
        cursor.close()
        conn.close()
        return "Wrong OTP. Try again."

    return render_template('verify_otp.html')


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = session.get('reset_email')
    if not email:
        return redirect(url_for('forgot_password'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) if DATABASE_URL else conn.cursor()
    cursor.execute(f"SELECT verified FROM password_resets WHERE email={P}", (email,))
    row = cursor.fetchone()

    is_verified = row['verified'] if DATABASE_URL else (row[0] if row else None)

    if not row or not is_verified:
        cursor.close()
        conn.close()
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if new_password != confirm_password:
            cursor.close()
            conn.close()
            return "Passwords do not match!"

        cursor.execute(f"UPDATE users SET password={P} WHERE email={P}", (new_password, email))
        cursor.execute(f"DELETE FROM password_resets WHERE email={P}", (email,))
        conn.commit()
        cursor.close()
        conn.close()

        session.pop('reset_email', None)
        flash("Password successfully reset! Please login with your new password.", "success")
        return redirect(url_for('login'))

    cursor.close()
    conn.close()
    return render_template('reset_password.html')


@app.route('/all-users')
def all_users():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) if DATABASE_URL else conn.cursor()
    cursor.execute("SELECT email, password FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    try:
        return str([dict(x) for x in users])
    except:
        return str([list(x) for x in users])


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
