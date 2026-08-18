import sqlite3
import hashlib
import os
import uuid
import secrets
import logging
from datetime import datetime, timedelta
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger("ragx.db_auth")

DB_PATH = settings.DATA_DIR / "users.db"

def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_auth_db():
    """
    Initializes SQLite tables for users, sessions, and activity logs.
    Seeds default admin account if no admin exists.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'USER',
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Activity Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        user_email TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        timestamp TEXT NOT NULL
    )
    """)

    # Indices for high performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_logs_ts ON activity_logs(timestamp)")

    conn.commit()

    # Seed Default Admin Account if missing
    cursor.execute("SELECT id FROM users WHERE role = 'ADMIN' LIMIT 1")
    admin_row = cursor.fetchone()
    if not admin_row:
        admin_email = "teamragx@gmail.com"
        cursor.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
        if not cursor.fetchone():
            salt = secrets.token_hex(16)
            password_hash = hash_password("teamrag123", salt)
            admin_id = f"usr_admin_{uuid.uuid4().hex[:8]}"
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
            INSERT INTO users (id, email, full_name, password_hash, salt, role, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (admin_id, admin_email, "System Administrator", password_hash, salt, "ADMIN", "ACTIVE", now_str, now_str))
            conn.commit()
            logger.info(f"Seeded default Admin account ({admin_email}).")

    conn.close()

def hash_password(password: str, salt: str) -> str:
    """
    Hashes a password using PBKDF2 HMAC SHA-256 with salt.
    """
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()

def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    computed = hash_password(password, salt)
    return secrets.compare_digest(computed, expected_hash)

# Initialize DB on module import
init_auth_db()
