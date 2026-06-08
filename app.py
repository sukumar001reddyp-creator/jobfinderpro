import os
import random
import sqlite3

# Python 3.14 + Cloud ఎన్విరాన్మెంట్ లో ఇంపోర్ట్ క్రాష్ అవ్వకుండా ప్రొటెక్షన్
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PS_VERSION = 2
except ModuleNotFoundError:
    try:
        # ఒకవేళ వెర్షన్ 3 ఇన్‌స్టాల్ అయితే దాన్ని వాడుకుంటుంది
        import psycopg
        from psycopg.rows import dict_row
        PS_VERSION = 3
    except ModuleNotFoundError:
        PS_VERSION = None

from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_mailman import Mail, EmailMessage

app = Flask(__name__)
app.secret_key = "jobfinder_super_stable_secret_key_2026"

# Flask-Mailman Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'jobfinderpro85@gmail.com'
app.config['MAIL_PASSWORD'] = 'eole ihak wvty vumv'

mail = Mail(app)

# ==================== SMART HYBRID DATABASE BLOCK ====================
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if DATABASE_URL:
        url = DATABASE_URL
        if "sslmode" not in url:
            url += "&sslmode=require" if "?" in url else "?sslmode=require"
        
        # వెర్షన్ ని బట్టి కరెక్ట్ డిక్షనరీ కర్సర్ ని అప్లై చేస్తుంది
        if PS_VERSION == 3:
            conn = psycopg.connect(url, row_factory=dict_row)
        else:
            conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
        return conn
    else:
        # Local SQLite
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        DB_PATH = os.path.join(BASE_DIR, "users.db")
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

P = "%s" if DATABASE_URL else "?"

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DATABASE_URL:
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
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            email VARCHAR(255) PRIMARY KEY,
            otp VARCHAR(10),
            verified BOOLEAN DEFAULT FALSE
        )
        """)
    else:
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
    print(f"Database initial boot warning: {str(db_init_err)}")
# ====================================================================
