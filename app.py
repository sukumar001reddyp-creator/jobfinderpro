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
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
# CORS ని ఇలా సెట్ చెయ్
CORS(app, resources={r"/api/*": {"origins": "*"}})

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

# Dynamic Placeholder (Postgres ki %s, SQLite ki ?)
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
        # Saved Searches Table for Cloud
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_searches (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255),
            role VARCHAR(255),
            location VARCHAR(255),
            experience VARCHAR(255),
            work_mode VARCHAR(255)
        )
        """)
        # Trending Skills Table for Cloud (Postgres)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS skill_trends (
            skill VARCHAR(255) PRIMARY KEY,
            search_count INTEGER DEFAULT 0
        )
        """)
        # 🌟 Kanban Job Tracker Table for Cloud (Postgres)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_applications (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255),
            company VARCHAR(255),
            role VARCHAR(255),
            status VARCHAR(50) DEFAULT 'Applied'
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
        # Saved Searches Table for Local
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            role TEXT,
            location TEXT,
            experience TEXT,
            work_mode TEXT
        )
        """)
        # Trending Skills Table for Local (SQLite)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS skill_trends (
            skill TEXT PRIMARY KEY,
            search_count INTEGER DEFAULT 0
        )
        """)
        # 🌟 Kanban Job Tracker Table for Local (SQLite)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            company TEXT,
            role TEXT,
            status TEXT DEFAULT 'Applied'
        )
        """)
        
    # Seed Default Skills Data smoothly without crashing
    default_skills = ['Python / Flask', 'React.js', 'Generative AI', 'SQL Databases', 'Cloud (AWS)', 'Video Editing']
    for skill in default_skills:
        try:
            if DATABASE_URL:
                cursor.execute("INSERT INTO skill_trends (skill, search_count) VALUES (%s, %s) ON CONFLICT (skill) DO NOTHING", (skill, 10))
            else:
                cursor.execute("INSERT OR IGNORE INTO skill_trends (skill, search_count) VALUES (?, ?)", (skill, 10))
        except:
            pass
        
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
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) if DATABASE_URL else conn.cursor()
    
    cursor.execute(f"SELECT skill, search_count FROM skill_trends ORDER BY search_count DESC LIMIT 6")
    trends = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if DATABASE_URL:
        graph_labels = [row['skill'] for row in trends]
        graph_data = [row['search_count'] for row in trends]
    else:
        graph_labels = [row[0] for row in trends]
        graph_data = [row[1] for row in trends]
        
    return render_template("index.html", graph_labels=graph_labels, graph_data=graph_data)

def get_indeed_domain(location):

    location = location.lower()

    if "hyderabad" in location or "bangalore" in location or "india" in location:
        return "https://in.indeed.com/jobs"

    elif "london" in location or "uk" in location:
        return "https://uk.indeed.com/jobs"

    elif "toronto" in location or "canada" in location:
        return "https://ca.indeed.com/jobs"

    else:
        return "https://www.indeed.com/jobs"


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
            session["user"] = user["email"] if DATABASE_URL else user[2]
            return redirect(url_for("dashboard"))

        return "Invalid Login Credentials"

    return render_template("login.html") 


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Profile information fetch
    cursor.execute(
        f"SELECT name, email, jobrole, location, experience FROM users WHERE email={P}",
        (session["user"],)
    )
    user = cursor.fetchone()
    
    # Saved search pipelines fetch
    cursor.execute(
        f"SELECT id, role, location, experience, work_mode FROM saved_searches WHERE email={P}",
        (session["user"],)
    )
    saved_queries = cursor.fetchall()
    cursor.close()
    
    # 🌟 Kanban Applications Pipeline Fetch Block (Cloud and Local Safe)
    cursor = conn.cursor(cursor_factory=RealDictCursor) if DATABASE_URL else conn.cursor()
    cursor.execute(
        f"SELECT id, company, role, status FROM job_applications WHERE email={P}",
        (session["user"],)
    )
    applications = cursor.fetchall()
    cursor.close()
    conn.close()

    if user is None:
        return "User session expired or not found."

    return render_template("dashboard.html", user=user, saved_queries=saved_queries, applications=applications)


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
    work_mode = request.args.get("work_mode", "").strip()
    indeed_domain = get_indeed_domain(location)

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) if DATABASE_URL else conn.cursor()

    if role:
        matched = False
        skills_to_check = ['Python', 'React', 'AI', 'SQL', 'AWS', 'Video']
        skill_mapping = {
            'Python': 'Python / Flask',
            'React': 'React.js',
            'AI': 'Generative AI',
            'SQL': 'SQL Databases',
            'AWS': 'Cloud (AWS)',
            'Video': 'Video Editing'
        }
        
        for s in skills_to_check:
            if s.lower() in role.lower():
                db_skill = skill_mapping[s]
                cursor.execute(f"UPDATE skill_trends SET search_count = search_count + 1 WHERE skill = {P}", (db_skill,))
                matched = True
                break
                
        if not matched:
            if DATABASE_URL:
                cursor.execute("INSERT INTO skill_trends (skill, search_count) VALUES (%s, 1) ON CONFLICT(skill) DO UPDATE SET search_count = skill_trends.search_count + 1", (role.title(),))
            else:
                cursor.execute("INSERT INTO skill_trends (skill, search_count) VALUES (?, 1) ON CONFLICT(skill) DO UPDATE SET search_count = search_count + 1", (role.title(),))
        conn.commit()

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
        work_mode=work_mode,
        indeed_domain=indeed_domain,
        logged_user=logged_user
    )


@app.route("/save-search", methods=["POST"])
def save_search():
    if "user" not in session:
        return redirect(url_for("login"))
    
    email = session["user"]
    role = request.form.get("role", "").strip()
    location = request.form.get("location", "").strip()
    experience = request.form.get("experience", "").strip()
    work_mode = request.form.get("work_mode", "").strip()

    if role or location or work_mode:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT INTO saved_searches (email, role, location, experience, work_mode) VALUES ({P}, {P}, {P}, {P}, {P})",
            (email, role, location, experience, work_mode)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash("Search pipeline saved successfully!", "success")
    
    return redirect(url_for("dashboard"))


@app.route("/delete-search/<int:search_id>")
def delete_search(search_id):
    if "user" not in session:
        return redirect(url_for("login"))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"DELETE FROM saved_searches WHERE id={P} AND email={P}", 
        (search_id, session["user"])
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("dashboard"))


# 🌟 KANBAN OPERATIONAL CORE ROUTES BACKEND PIPELINE
@app.route("/add-application", methods=["POST"])
def add_application():
    if "user" not in session: return redirect(url_for("login"))
    company = request.form.get("company", "").strip()
    role = request.form.get("role", "").strip()
    status = request.form.get("status", "Applied")
    
    if company and role:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT INTO job_applications (email, company, role, status) VALUES ({P}, {P}, {P}, {P})",
            (session["user"], company, role, status)
        )
        conn.commit()
        cursor.close()
        conn.close()
    return redirect(url_for("dashboard"))

@app.route("/update-application-status/<int:app_id>/<string:new_status>")
def update_application_status(app_id, new_status):
    if "user" not in session: return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE job_applications SET status={P} WHERE id={P} AND email={P}",
        (new_status, app_id, session["user"])
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/delete-application/<int:app_id>")
def delete_application(app_id):
    if "user" not in session: return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"DELETE FROM job_applications WHERE id={P} AND email={P}",
        (app_id, session["user"])
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/ai-helper")
def ai_helper():
    return render_template("ai_helper.html")


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


@app.route('/resume-builder')
def resume_builder():
    logged_user = session.get('user')
    user_data = None
    
    if logged_user:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor) if DATABASE_URL else conn.cursor()
            cursor.execute(f"SELECT name, email, jobrole, location FROM users WHERE email={P}", (logged_user,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if row:
                if DATABASE_URL:
                    user_data = (row['name'], row['email'], row['jobrole'], row['location'], '')
                else:
                    user_data = (row[0], row[1], row[2], row[3], '')
        except Exception as e:
            print(f"Database error but bypassing: {e}")
            user_data = None
            
    return render_template('resume_builder.html', user_data=user_data, logged_user=logged_user)


@app.route('/mock-interview')
def mock_interview():
    logged_user = session.get('user')
    user_role = ""
    
    if logged_user:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor) if DATABASE_URL else conn.cursor()
            cursor.execute(f"SELECT jobrole FROM users WHERE email={P}", (logged_user,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if row:
                user_role = row['jobrole'] if DATABASE_URL else row[0]
        except:
            pass
            
    return render_template('interview_bot.html', logged_user=logged_user, user_role=user_role)

from flask import jsonify

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) if DATABASE_URL else conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE email={P} AND password={P}", (email, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({"status": "success", "email": email}), 200
    return jsonify({"status": "error", "message": "Invalid Credentials"}), 401

@app.route('/api/dashboard/<email>')
def get_dashboard(email):
    data = {
        "user": {"name": "Sukum"},
        "applications": [
            {"company": "Google", "role": "Developer", "status": "Applied"}
        ]
    }
    return jsonify(data)
if __name__ == "__main__":
    app.run(debug=True)
