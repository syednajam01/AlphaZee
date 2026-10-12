"""Versioned salted PBKDF2-SHA256 hashes; no plaintext credential defaults."""
import hashlib
import hmac
import secrets

ITERATIONS = 600_000


def hash_password(password: str) -> str:
    if not 12 <= len(password) <= 128:
        raise ValueError('Password must contain 12 to 128 characters.')
    salt = secrets.token_hex(32)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f'pbkdf2_sha256${ITERATIONS}${salt}${digest}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt, expected = encoded.split('$')
        if scheme != 'pbkdf2_sha256' or int(rounds) != ITERATIONS or len(salt) != 64 or len(expected) != 64:
            return False
        if len(password) > 128:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


# Unknown usernames incur the same password work without a real credential.
DUMMY_HASH = f'pbkdf2_sha256${ITERATIONS}$' + '00' * 32 + '$' + '00' * 32
