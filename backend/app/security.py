import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import jwt
from cryptography.fernet import Fernet
from passlib.context import CryptContext
from backend.app.config import settings

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
ALGORITHM = "HS256"

# In-memory rate limiting for login attempts: ip -> [timestamps]
login_attempts: Dict[str, list[float]] = {}
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def encrypt_token(raw_token: str) -> str:
    """Encrypt a sensitive Telegram Bot token at rest using Fernet."""
    if not raw_token:
        return ""
    f = Fernet(settings.get_encryption_key())
    return f.encrypt(raw_token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a stored Telegram Bot token."""
    if not encrypted_token:
        return ""
    f = Fernet(settings.get_encryption_key())
    return f.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")


def mask_token(raw_token: str) -> str:
    """Safely mask a token for UI presentation (e.g. 123456789:ABC...wxyz)."""
    if not raw_token:
        return ""
    if len(raw_token) <= 10:
        return "********"
    prefix = raw_token[:6]
    suffix = raw_token[-4:]
    return f"{prefix}...{suffix}"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def check_login_rate_limit(client_ip: str) -> bool:
    """Return True if request is within limits, False if rate limited."""
    now = time.time()
    attempts = login_attempts.get(client_ip, [])
    # Filter attempts within the window
    attempts = [t for t in attempts if now - t < LOGIN_WINDOW_SECONDS]
    login_attempts[client_ip] = attempts
    return len(attempts) < MAX_LOGIN_ATTEMPTS


def record_failed_login(client_ip: str):
    """Record a failed login attempt for rate limiting."""
    now = time.time()
    attempts = login_attempts.get(client_ip, [])
    attempts.append(now)
    login_attempts[client_ip] = attempts


def reset_login_attempts(client_ip: str):
    """Reset failed attempts on successful login."""
    login_attempts.pop(client_ip, None)
