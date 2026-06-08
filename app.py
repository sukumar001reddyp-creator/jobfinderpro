import random
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for
from flask_mail import Mail, Message
from flask import Flask, render_template, request, redirect, session, url_for, flash

app = Flask(__name__)
app.secret_key = "jobfinder_secret"

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'jobfinderpro85@gmail.com'
app.config['MAIL_PASSWORD'] = 'eole ihak wvty vumv'

mail = Mail(app)

def get_db_connection():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row  # Enforces dictionary-like access
    return conn

# Database Initialization
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

init_db()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        jobrole = request.form.get("jobrole")
        location = request.form.get("location")
        experience = request.form.get("experience")

        if not all([name, email, password, jobrole, location, experience]):
            return "All fields are required!"

        if password != confirm_password:
            return "Passwords do not match"

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users (name, email, password, jobrole, location, experience)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, email, password, jobrole, location, experience)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            conn.close()
            return "Email already exists"
    
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

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

    # Dynamic database matching logic
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
        email = request.form.get('email')
        
        # Verify if email exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            return "Email address not registered!"

        otp = str(random.randint(100000, 999999))
        session['otp'] = otp
        session['reset_email'] = email

        msg = Message(
            "JobFinder Password Reset OTP",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"Hello,\n\nYour OTP is: {otp}\n\nValid for 10 mins."

        try:
            mail.send(msg)
            return redirect(url_for('verify_otp'))
        except Exception as e:
            return f"Error sending email: {str(e)}"

    return render_template('forgot_password.html')


@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reset_email' not in session:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        # Added .strip() to remove accidental spaces typed by user
        entered_otp = request.form.get('otp', '').strip()
        saved_otp = str(session.get('otp', ''))

        # Direct string to string strict check
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
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            return "Passwords do not match!"

        email = session['reset_email']
        
        # Database verification update
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password=? WHERE email=?", (new_password, email))
        conn.commit()
        conn.close()

        # Session clean-up tracking parameters 
        session.pop('otp', None)
        session.pop('reset_email', None)
        session.pop('otp_verified', None)

        # Flash dynamic setup (Only single string insertion)
        flash("Password successfully reset! Please login with your new password.", "success")

        return redirect(url_for('login'))

    return render_template('reset_password.html')

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))


@app.route('/test-mail')
def test_mail():
    msg = Message(
        'Test Mail',
        sender=app.config['MAIL_USERNAME'],
        recipients=['jobfinderpro85@gmail.com']
    )
    msg.body = 'Mail working bro'
    try:
        mail.send(msg)
        return "Mail Sent Successfully"
    except Exception as e:
        return f"Mail setup broken: {str(e)}"


if __name__ == "__main__":
    app.run(debug=True)
