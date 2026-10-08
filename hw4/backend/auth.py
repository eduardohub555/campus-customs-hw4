"""Accounts and passwords for Campus Customs.

Passwords are never stored. What goes in the ``users`` table is a
PBKDF2-HMAC-SHA256 derivation, in the same format the seeded rows already use:

    pbkdf2_sha256$<salt>$<64 hex characters>

The parameters were read back off the seed data so the existing test user keeps
working: SHA-256, 120,000 iterations, a per-user random salt, a 32-byte digest.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
from typing import Any

import db

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000
SALT_BYTES = 8  # 16 hex characters, matching the seeded rows
MIN_PASSWORD_LENGTH = 8

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DIGIT_PATTERN = re.compile(r"\d")
# "Special" means anything that is not a letter, a digit or a space: . - ! # and so on.
SPECIAL_PATTERN = re.compile(r"[^A-Za-z0-9\s]")

# Sessions live in memory: a restart signs everybody out. Good enough for the
# course project, and it keeps tokens out of the database entirely.
_SESSIONS: dict[str, int] = {}


class AuthError(Exception):
    """Raised with a message that is safe to show the person signing in."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


# --------------------------------------------------------------------------
# passwords
# --------------------------------------------------------------------------

def _derive(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS
    ).hex()


def hash_password(password: str) -> str:
    """Derive a storable hash with a fresh random salt."""
    salt = secrets.token_hex(SALT_BYTES)
    return f"{ALGORITHM}${salt}${_derive(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored hash.

    Comparison is constant-time so a wrong password cannot be narrowed down by
    timing, and case-sensitive because the derivation is over the exact bytes.
    """
    try:
        algorithm, salt, expected = stored.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    return hmac.compare_digest(_derive(password, salt), expected)


# A hash of a value nobody can log in with. Verifying against it when an email
# is unknown keeps the failed-login timing the same either way, so the response
# time cannot be used to discover which emails have accounts.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def _clean_email(email: str) -> str:
    """Emails are matched case-insensitively; passwords never are."""
    value = email.strip().lower()
    if not EMAIL_PATTERN.match(value):
        raise AuthError("That does not look like an email address.")
    return value


def _clean_name(value: str, field: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise AuthError(f"{field} is required.")
    return cleaned


def _check_password(password: str, confirmation: str) -> None:
    if password != confirmation:
        # Exact string comparison, so "Password" and "password" do not match.
        raise AuthError("The two passwords do not match.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if not DIGIT_PATTERN.search(password):
        raise AuthError("Password must include at least one number.")
    if not SPECIAL_PATTERN.search(password):
        raise AuthError("Password must include at least one special character, such as a period.")


# --------------------------------------------------------------------------
# users
# --------------------------------------------------------------------------

def _public(row: sqlite3.Row) -> dict[str, Any]:
    """The user fields the browser is allowed to see. Never the hash."""
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "first_name": row["first_name"] or row["name"].split(" ")[0],
        "last_name": row["last_name"] or "",
        "created_at": row["created_at"],
    }


def register(
    first_name: str, last_name: str, email: str, password: str, confirm_password: str
) -> tuple[str, dict[str, Any]]:
    first = _clean_name(first_name, "First name")
    last = _clean_name(last_name, "Last name")
    address = _clean_email(email)
    _check_password(password, confirm_password)

    with db.connect_rw() as conn:
        taken = conn.execute(
            "SELECT 1 FROM users WHERE lower(email) = ?", (address,)
        ).fetchone()
        if taken:
            raise AuthError("An account already uses that email address.", status=409)

        cursor = conn.execute(
            """INSERT INTO users (name, email, password_hash, first_name, last_name)
               VALUES (?, ?, ?, ?, ?)""",
            (f"{first} {last}", address, hash_password(password), first, last),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()

    return _open_session(row["id"]), _public(row)


def login(email: str, password: str) -> tuple[str, dict[str, Any]]:
    address = email.strip().lower()
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE lower(email) = ?", (address,)
        ).fetchone()

    if row is None:
        verify_password(password, _DUMMY_HASH)  # keep the timing even
        raise AuthError("Email or password is incorrect.", status=401)
    if not verify_password(password, row["password_hash"]):
        raise AuthError("Email or password is incorrect.", status=401)

    return _open_session(row["id"]), _public(row)


# --------------------------------------------------------------------------
# sessions
# --------------------------------------------------------------------------

def _open_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = user_id
    return token


def current_user(token: str | None) -> dict[str, Any] | None:
    """Resolve a bearer token to a user, or None if it is not a live session."""
    if not token:
        return None
    user_id = _SESSIONS.get(token)
    if user_id is None:
        return None
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        _SESSIONS.pop(token, None)
        return None
    return _public(row)


def logout(token: str | None) -> None:
    if token:
        _SESSIONS.pop(token, None)
