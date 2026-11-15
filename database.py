"""
database.py — PostgreSQL connection & SHA-256 User Authentication.
"""
from __future__ import annotations

import hashlib
import os

try:
    import psycopg2
    HAS_PG = True
except ImportError:
    HAS_PG = False


def get_db_connection():
    if not HAS_PG:
        return None
    try:
        return psycopg2.connect(
            dbname=os.getenv("DB_NAME", "universal_ai_futures_bot"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),  # Apna PostgreSQL password yahan likhein
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            connect_timeout=2,
        )
    except Exception:
        return None


def hash_pwd(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username: str, password: str) -> tuple[bool, str]:
    conn = get_db_connection()
    if not conn:
        return False, "PostgreSQL offline. Password check karein ya 'Instant Quant Desk' button use karein."
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("SELECT id FROM users WHERE username = %s;", (username,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return False, "Yeh username pehle se PostgreSQL mein mojood hai!"
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s);",
            (username, hash_pwd(password)),
        )
        conn.commit()
        cur.close()
        conn.close()
        return True, "Account PostgreSQL mein ban gaya! Ab Login karein."
    except Exception as e:
        return False, f"Database error: {e}"


def verify_user(username: str, password: str) -> tuple[bool, str]:
    conn = get_db_connection()
    if not conn:
        return False, "PostgreSQL connection failed! Service ya password check karein."
    try:
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE username = %s;", (username,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        if res and res[0] == hash_pwd(password):
            return True, "Login successful!"
        return False, "Ghalat username ya password!"
    except Exception as e:
        return False, f"Database error: {e}"