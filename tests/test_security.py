import pytest
import time
from backend.app.security import (
    verify_password,
    get_password_hash,
    encrypt_token,
    decrypt_token,
    mask_token,
    create_access_token,
    decode_access_token,
    check_login_rate_limit,
    record_failed_login,
    reset_login_attempts,
)


def test_password_hashing():
    password = "SuperSecretPassword123!"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_token_encryption_and_masking():
    raw_token = "123456789:ABCdefGhIjkLmNoPqRsTuVwXyZ"
    encrypted = encrypt_token(raw_token)
    assert encrypted != raw_token

    decrypted = decrypt_token(encrypted)
    assert decrypted == raw_token

    masked = mask_token(raw_token)
    assert masked == "123456...wXyZ"
    assert raw_token not in masked


def test_jwt_token_lifecycle():
    data = {"sub": "admin_user", "role": "admin"}
    token = create_access_token(data)
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "admin_user"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_login_rate_limiting():
    ip = "192.168.1.100"
    reset_login_attempts(ip)

    # Initial check should pass
    assert check_login_rate_limit(ip) is True

    # Record 4 failed attempts
    for _ in range(4):
        record_failed_login(ip)
    assert check_login_rate_limit(ip) is True

    # 5th failed attempt hits the limit
    record_failed_login(ip)
    assert check_login_rate_limit(ip) is False

    # Resetting clears attempts
    reset_login_attempts(ip)
    assert check_login_rate_limit(ip) is True
