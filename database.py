"""
database.py — Hybrid PostgreSQL (Local + Cloud URI) & Cloud-Safe Fallback Auth.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import os
import sqlite3
import streamlit as st

try:
    import psycopg2
    HAS_PG = True
except ImportError:
    HAS_PG = False

SQLITE_FALLBACK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloud_users.db")


def get_pg_connection():
    if not HAS_PG:
        return None
    try:
        if "DATABASE_URL" in st.secrets:
            return psycopg2.connect(st.secrets["DATABASE_URL"], connect_timeout=3)
        if "postgres" in st.secrets and "url" in st.secrets["postgres"]:
            return psycopg2.connect(st.secrets["postgres"]["url"], connect_timeout=3)
    except Exception:
        pass

    try:
        return psycopg2.connect(
            dbname=os.getenv("DB_NAME", "universal_ai_futures_bot"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),  # Configure via environment
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            connect_timeout=2,
        )
    except Exception:
        return None


def hash_pwd(password: str) -> str:
    """Create a salted password hash for new users."""
    iterations = 310000
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_pwd(password: str, stored: str) -> bool:
    """Verify PBKDF2 hashes and preserve compatibility with legacy SHA256 logins."""
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iters, salt, expected = stored.split("$", 3)
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iters)
            )
            return hmac.compare_digest(actual, bytes.fromhex(expected))
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), stored)


def register_user(username: str, password: str) -> tuple[bool, str]:
    conn = get_pg_connection()
    if conn:
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
            return True, "Account PostgreSQL mein kamiyabi se ban gaya! Ab Login karein."
        except Exception as e:
            return False, f"PostgreSQL Error: {e}"

    try:
        sconn = sqlite3.connect(SQLITE_FALLBACK)
        cur = sconn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("SELECT id FROM users WHERE username = ?;", (username,))
        if cur.fetchone():
            sconn.close()
            return False, "Yeh username pehle se mojood hai!"
        cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?);", (username, hash_pwd(password)))
        sconn.commit()
        sconn.close()
        return True, "Account kamiyabi se ban gaya! Ab Login karein."
    except Exception as e:
        return False, f"Database error: {e}"


def verify_user(username: str, password: str) -> tuple[bool, str]:
    conn = get_pg_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT password_hash FROM users WHERE username = %s;", (username,))
            res = cur.fetchone()
            cur.close()
            conn.close()
            if res and verify_pwd(password, res[0]):
                return True, "Login successful!"
            return False, "Ghalat username ya password!"
        except Exception as e:
            return False, f"PostgreSQL Error: {e}"

    try:
        sconn = sqlite3.connect(SQLITE_FALLBACK)
        cur = sconn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("SELECT password_hash FROM users WHERE username = ?;", (username,))
        res = cur.fetchone()
        sconn.close()
        if res and verify_pwd(password, res[0]):
            return True, "Login successful!"
        return False, "Ghalat username ya password! Pehle Create Account tab se account banayein."
    except Exception as e:
        return False, f"Database error: {e}"