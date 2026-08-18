import uuid
import secrets
import logging
from datetime import datetime, timedelta
from app.core.db_auth import get_db_connection, hash_password, verify_password

logger = logging.getLogger("ragx.auth_service")

class AuthService:
    @staticmethod
    def log_activity(user_id: str, user_name: str, user_email: str, action: str, details: str = ""):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            log_id = f"act_{uuid.uuid4().hex[:12]}"
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
            INSERT INTO activity_logs (id, user_id, user_name, user_email, action, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (log_id, user_id, user_name, user_email, action, details, now_str))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log activity '{action}': {e}")

    @classmethod
    def register_user(cls, email: str, full_name: str, password: str, role: str = "USER") -> dict:
        email_clean = email.strip().lower()
        full_name_clean = full_name.strip()
        
        if not email_clean or "@" not in email_clean:
            raise ValueError("Invalid email address format.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters long.")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
        if cursor.fetchone():
            conn.close()
            raise ValueError("An account with this email address already exists.")

        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        salt = secrets.token_hex(16)
        pwd_hash = hash_password(password, salt)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        INSERT INTO users (id, email, full_name, password_hash, salt, role, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, email_clean, full_name_clean, pwd_hash, salt, role, "ACTIVE", now_str, now_str))
        conn.commit()
        conn.close()

        cls.log_activity(user_id, full_name_clean, email_clean, "Account Registered", f"New user account created with role '{role}'.")
        return cls.create_session(user_id)

    @classmethod
    def login_user(cls, email: str, password: str) -> dict:
        email_clean = email.strip().lower()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email_clean,))
        user = cursor.fetchone()
        conn.close()

        if not user or not verify_password(password, user["salt"], user["password_hash"]):
            raise ValueError("Invalid email or password.")

        if user["status"] != "ACTIVE":
            raise ValueError("This account has been disabled. Please contact administrator.")

        cls.log_activity(user["id"], user["full_name"], user["email"], "Login", "User logged in successfully.")
        return cls.create_session(user["id"])

    @staticmethod
    def create_session(user_id: str) -> dict:
        token = f"ragx_tok_{secrets.token_hex(24)}"
        conn = get_db_connection()
        cursor = conn.cursor()

        now = datetime.now()
        expires = now + timedelta(days=7)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        expires_str = expires.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        INSERT INTO sessions (token, user_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """, (token, user_id, now_str, expires_str))

        cursor.execute("SELECT id, email, full_name, role, status, created_at FROM users WHERE id = ?", (user_id,))
        user_info = dict(cursor.fetchone())
        conn.commit()
        conn.close()

        return {
            "token": token,
            "user": user_info
        }

    @classmethod
    def validate_session(cls, token: str) -> dict | None:
        if not token:
            return None

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT s.token, s.expires_at, u.id, u.email, u.full_name, u.role, u.status, u.created_at
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ?
        """, (token,))
        session = cursor.fetchone()
        conn.close()

        if not session:
            return None

        # Check expiration
        exp = datetime.strptime(session["expires_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > exp:
            return None

        if session["status"] != "ACTIVE":
            return None

        return {
            "id": session["id"],
            "email": session["email"],
            "full_name": session["full_name"],
            "role": session["role"],
            "status": session["status"],
            "created_at": session["created_at"]
        }

    @classmethod
    def logout_session(cls, token: str, user: dict = None):
        if not token:
            return
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()

        if user:
            cls.log_activity(user["id"], user["full_name"], user["email"], "Logout", "User logged out.")

    @classmethod
    def update_profile(cls, user_id: str, new_name: str) -> dict:
        name_clean = new_name.strip()
        if not name_clean:
            raise ValueError("Full name cannot be empty.")

        conn = get_db_connection()
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET full_name = ?, updated_at = ? WHERE id = ?", (name_clean, now_str, user_id))
        
        cursor.execute("SELECT id, email, full_name, role, status, created_at FROM users WHERE id = ?", (user_id,))
        updated_user = dict(cursor.fetchone())
        conn.commit()
        conn.close()

        cls.log_activity(user_id, updated_user["full_name"], updated_user["email"], "Name Changed", f"Display name updated to '{name_clean}'.")
        return updated_user

    @classmethod
    def change_password(cls, user_id: str, current_password: str, new_password: str):
        if len(new_password) < 6:
            raise ValueError("New password must be at least 6 characters long.")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()

        if not user or not verify_password(current_password, user["salt"], user["password_hash"]):
            conn.close()
            raise ValueError("Current password is incorrect.")

        new_salt = secrets.token_hex(16)
        new_pwd_hash = hash_password(new_password, new_salt)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        UPDATE users SET password_hash = ?, salt = ?, updated_at = ? WHERE id = ?
        """, (new_pwd_hash, new_salt, now_str, user_id))
        
        # Invalidate old sessions
        cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

        cls.log_activity(user["id"], user["full_name"], user["email"], "Password Changed", "User changed password.")

    @classmethod
    def delete_account(cls, user_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()

        if user:
            cls.log_activity(user["id"], user["full_name"], user["email"], "Account Deleted", "User deleted their account.")
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            conn.commit()
        conn.close()

    @classmethod
    def get_all_users_admin(cls) -> list[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT u.id, u.email, u.full_name, u.role, u.status, u.created_at, u.updated_at
        FROM users u
        ORDER BY u.created_at DESC
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @classmethod
    def get_activity_logs(cls, limit: int = 100) -> list[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
