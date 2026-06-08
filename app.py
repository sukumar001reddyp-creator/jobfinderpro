import os
import random
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_mail import Mail, Message

app = Flask(__name__)

# Render production rules security wrapper sessions tracking fix
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'jobfinder_secret_strongly_hashed_2026')

# Flask-Mail Strict Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'jobfinderpro85@gmail.com'
app.config['MAIL_PASSWORD'] = 'eole ihak wvty vumv'

# Fail safe dynamic adjustments for cloud proxy buffers
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True

mail = Mail(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")

def get_db_connection():
    # check_same_thread constraints handle matching dynamic queries pipeline lock fix
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
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

# Cloud instance safety execution initialization validation block bypass triggers
try:
    init_db()
except Exception as db_init_err:
    print(f"Cloud DB initial runtime notice: {str(db_init_err)}")
# ====================================================================

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
                """
                INSERT INTO users (name, email, password, jobrole, location, experience)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, email, password, jobrole, location, experience)
            )
            conn.commit()
            success = True
        except sqlite3.IntegrityError:
            error_msg = "Email already exists"
        except Exception as e:
            error_msg = f"Live Database Entry Error: {str(e)}"
        finally:
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
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = user["email"]
            return redirect(url_for("dashboard"))

        return "Invalid Login Credentials"

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, email, jobrole, location, experience FROM users WHERE email=?", (session["user"],))
    user = cursor.fetchone()
    conn.close()

    if user is None:
        return "User session expired or not found."

    return render_template("dashboard.html", user=user)


@app.route("/search")
def search():
    role = request.args.get("role", "").strip()
    location = request.args.get("location", "").strip()
    experience = request.args.get("experience", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT name, email, jobrole, location, experience FROM users WHERE 1=1"
    params = []

    if role:
        query += " AND jobrole LIKE ?"
        params.append(f"%{role}%")
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if experience:
        query += " AND experience = ?"
        params.append(experience)

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    return render_template(
        "search.html",
        results=results,
        role=role,
        location=location,
        experience=experience
    )


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            return "Email address not registered! Please crosscheck."

        otp = str(random.randint(100000, 999999))
        session['otp'] = otp
        session['reset_email'] = email

        msg = Message(
            "JobFinder Password Reset OTP",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"Hello,\n\nYour JobFinder password reset OTP is: {otp}\n\nValid for 10 minutes.\n\nTeam JobFinder"

        try:
            mail.send(msg)
            return redirect(url_for('verify_otp'))
        except Exception as e:
            return f"SMTP Mail Transfer Denied by Live Proxy Host. Details: {str(e)}"

    return render_template('forgot_password.html')


@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reset_email' not in session:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        saved_otp = str(session.get('otp', ''))

        if entered_otp == saved_otp and entered_otp != '':
            session['otp_verified'] = True
            return redirect(url_for('reset_password'))

        return "Wrong OTP. Try again."

    return render_template('verify_otp.html')


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if not session.get('otp_verified') or 'reset_email' not in session:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if new_password != confirm_password:
            return "Passwords do not match!"

        email = session['reset_email']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password=? WHERE email=?", (new_password, email))
        conn.commit()
        conn.close()

        session.pop('otp', None)
        session.pop('reset_email', None)
        session.pop('otp_verified', None)

        flash("Password successfully reset! Please login with your new password.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html')

@app.route('/all-users')
def all_users():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT email,password FROM users")
    users = cursor.fetchall()

    conn.close()

    return str([dict(x) for x in users])


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))


if __name__ == "__main__":
    # Local fallback startup configurations
    app.run(debug=True)
