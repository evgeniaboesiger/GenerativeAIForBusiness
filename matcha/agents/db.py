"""
MATCHA - Secure user accounts & profile storage.

This module provides:
1. User registration and login (passwords hashed with PBKDF2 - never stored in plain text)
2. Per-user profile storage in SQLite
3. CV text encrypted with Fernet symmetric encryption

Security notes:
- Passwords: salted PBKDF2-HMAC-SHA256 hashing (industry standard)
- CV data: encrypted with a per-install encryption key stored in a gitignored file
- The database and key file are excluded from git (see .gitignore)
"""

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

# Paths (relative to this file's directory)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "matcha_users.db")
KEY_FILE = os.path.join(BASE_DIR, ".matcha_key")

# PBKDF2 iteration count (high = more secure, slightly slower)
PBKDF2_ITERATIONS = 200_000


# ---------------------------------------------------------------------- #
#  Encryption helpers (for CV / sensitive profile data)
# ---------------------------------------------------------------------- #
def _get_or_create_key() -> bytes:
    """Load the Fernet key, or generate and save one on first run."""
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        # Should not happen (cryptography is a dependency) but fail cleanly.
        raise RuntimeError("The 'cryptography' package is required. Run: pip install cryptography")

    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()

    key = Fernet.generate_key()
    # Create file with restricted permissions where possible.
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    try:
        os.chmod(KEY_FILE, 0o600)  # Owner read/write only (Unix). No-op on Windows.
    except Exception:
        pass
    return key


def encrypt_text(plain: str) -> str:
    """Encrypt a string so it is not readable in the database file."""
    from cryptography.fernet import Fernet
    fernet = Fernet(_get_or_create_key())
    return fernet.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_text(token: str) -> str:
    """Decrypt a string previously encrypted with encrypt_text."""
    from cryptography.fernet import Fernet
    fernet = Fernet(_get_or_create_key())
    return fernet.decrypt(token.encode("utf-8")).decode("utf-8")


# ---------------------------------------------------------------------- #
#  Password hashing (never stores the plain text password)
# ---------------------------------------------------------------------- #
def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hash a password with PBKDF2. Returns (hash_hex, salt_hex)."""
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS
    )
    return digest.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Check a password against its stored hash."""
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS
    )
    return hmac.compare_digest(digest.hex(), stored_hash)


# ---------------------------------------------------------------------- #
#  Database helpers
# ---------------------------------------------------------------------- #
def get_connection() -> sqlite3.Connection:
    """Open a connection to the SQLite database and create tables if needed."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'candidate',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            cv_text_encrypted TEXT,
            profile_json_encrypted TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS saved_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_id TEXT,
            job_title TEXT,
            company TEXT,
            score REAL,
            saved_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS candidate_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            prefs_json_encrypted TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS submitted_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_id TEXT,
            job_title TEXT NOT NULL,
            company TEXT,
            status TEXT NOT NULL DEFAULT 'under_review',
            submitted_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()


# ---------------------------------------------------------------------- #
#  User operations
# ---------------------------------------------------------------------- #
def register_user(email: str, password: str, full_name: str, role: str = "candidate") -> Dict[str, Any]:
    """
    Create a new user account.

    Raises ValueError if the email is already registered.
    """
    email = (email or "").strip().lower()
    full_name = (full_name or "").strip()
    if not email or "@" not in email:
        raise ValueError("Please enter a valid email address.")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    if not full_name:
        raise ValueError("Please enter your full name.")

    conn = get_connection()
    try:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            raise ValueError("An account with this email already exists. Please log in instead.")

        password_hash, salt = hash_password(password)
        conn.execute(
            "INSERT INTO users (full_name, email, password_hash, salt, role) VALUES (?, ?, ?, ?, ?)",
            (full_name, email, password_hash, salt, role)
        )
        conn.commit()

        row = conn.execute("SELECT id, full_name, email, role FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def login_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Verify credentials. Returns the user dict on success, None on failure.
    """
    email = (email or "").strip().lower()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, full_name, email, password_hash, salt, role FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        if row is None:
            return None
        if not verify_password(password, row["password_hash"], row["salt"]):
            return None
        return {
            "id": row["id"],
            "full_name": row["full_name"],
            "email": row["email"],
            "role": row["role"]
        }
    finally:
        conn.close()


def update_user_name(user_id: int, full_name: str) -> None:
    """Update the display name of an existing account."""
    full_name = (full_name or "").strip()
    if not full_name:
        raise ValueError("Name cannot be empty.")
    conn = get_connection()
    try:
        cur = conn.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, user_id))
        if cur.rowcount == 0:
            raise ValueError("User not found.")
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------- #
#  Submitted applications (job + status tracked on the account page)
# ---------------------------------------------------------------------- #
def save_submitted_application(user_id: int, job: Dict[str, Any],
                               status: str = "under_review") -> None:
    """Record that the candidate submitted an application for a job."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO submitted_applications (user_id, job_id, job_title, company, status) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, job.get("id"), job.get("title", ""), job.get("company", ""), status)
        )
        conn.commit()
    finally:
        conn.close()


def load_submitted_applications(user_id: int) -> List[Dict[str, Any]]:
    """Return the candidate's submitted applications, newest first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT job_id, job_title, company, status, submitted_at "
            "FROM submitted_applications WHERE user_id = ? "
            "ORDER BY submitted_at DESC, id DESC",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------- #
#  Profile operations (CV stored encrypted)
# ---------------------------------------------------------------------- #
def save_profile(user_id: int, cv_text: str, profile_json: Dict[str, Any]) -> None:
    """Save (or update) the user's CV and extracted profile, both encrypted."""
    cv_enc = encrypt_text(cv_text) if cv_text else None
    profile_enc = encrypt_text(json.dumps(profile_json, ensure_ascii=False)) if profile_json else None

    conn = get_connection()
    try:
        existing = conn.execute("SELECT id FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE profiles SET cv_text_encrypted = ?, profile_json_encrypted = ?, "
                "updated_at = datetime('now') WHERE user_id = ?",
                (cv_enc, profile_enc, user_id)
            )
        else:
            conn.execute(
                "INSERT INTO profiles (user_id, cv_text_encrypted, profile_json_encrypted) VALUES (?, ?, ?)",
                (user_id, cv_enc, profile_enc)
            )
        conn.commit()
    finally:
        conn.close()


def load_profile(user_id: int) -> Optional[Dict[str, Any]]:
    """Load the user's saved profile. Returns a dict with cv_text and profile, or None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT cv_text_encrypted, profile_json_encrypted, updated_at FROM profiles WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        if row is None:
            return None

        result = {"updated_at": row["updated_at"]}
        if row["cv_text_encrypted"]:
            result["cv_text"] = decrypt_text(row["cv_text_encrypted"])
        if row["profile_json_encrypted"]:
            result["profile"] = json.loads(decrypt_text(row["profile_json_encrypted"]))
        return result
    finally:
        conn.close()


# ---------------------------------------------------------------------- #
#  Candidate preferences (stored separately from professional facts, encrypted)
# ---------------------------------------------------------------------- #
def save_preferences(user_id: int, prefs: Dict[str, Any]) -> None:
    """
    Upsert the candidate's structured employment preferences.
    Stored encrypted just like CV data; kept separate from the professional
    profile so factual qualifications and preference data stay distinct.
    """
    prefs_enc = encrypt_text(json.dumps(prefs, ensure_ascii=False))

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM candidate_preferences WHERE user_id = ?", (user_id,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE candidate_preferences SET prefs_json_encrypted = ?, "
                "updated_at = datetime('now') WHERE user_id = ?",
                (prefs_enc, user_id)
            )
        else:
            conn.execute(
                "INSERT INTO candidate_preferences (user_id, prefs_json_encrypted) VALUES (?, ?)",
                (user_id, prefs_enc)
            )
        conn.commit()
    finally:
        conn.close()


def load_preferences(user_id: int) -> Optional[Dict[str, Any]]:
    """Return the candidate's stored preferences dict, or None if never saved."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT prefs_json_encrypted, updated_at FROM candidate_preferences "
            "WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        if row is None or not row["prefs_json_encrypted"]:
            return None
        prefs = json.loads(decrypt_text(row["prefs_json_encrypted"]))
        prefs["_updated_at"] = row["updated_at"]
        return prefs
    finally:
        conn.close()


# ---------------------------------------------------------------------- #
#  Simple in-memory session (per browser session, not persistent)
# ---------------------------------------------------------------------- #
def init_session():
    """Initialize (or lazily create) the auth session state keys."""
    import streamlit as st
    if "user" not in st.session_state:
        st.session_state.user = None


# ---------------------------------------------------------------------- #
#  CLI self-test
# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    print("Running database self-test...")

    # Password hashing test
    h, s = hash_password("secret123")
    assert verify_password("secret123", h, s), "Password verification failed"
    assert not verify_password("wrong", h, s), "Wrong password should fail"
    print("[OK] Password hashing")

    # Encrypt/decrypt test
    token = encrypt_text("Sophie's private CV content")
    plain = decrypt_text(token)
    assert plain == "Sophie's private CV content", "Encryption round-trip failed"
    print("[OK] CV encryption")

    # Register / login test
    test_email = "test@example.com"
    register_user(test_email, "password123", "Test User")
    user = login_user(test_email, "password123")
    assert user is not None, "Login failed"
    assert login_user(test_email, "wrongpass") is None, "Wrong password should not log in"
    print(f"[OK] Register + login (user id={user['id']})")

    # Profile save / load test
    fake_profile = {"personal_info": {"name": "Test"}, "skills": ["Python"]}
    save_profile(user["id"], "CV TEXT SECRET", fake_profile)
    loaded = load_profile(user["id"])
    assert loaded is not None, "Profile not saved"
    assert loaded["cv_text"] == "CV TEXT SECRET", "CV text mismatch"
    assert loaded["profile"]["skills"] == ["Python"], "Profile mismatch"
    print("[OK] Encrypted profile save/load")

    print("\nALL DATABASE TESTS PASSED")