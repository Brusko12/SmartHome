import base64
import hashlib
import hmac
import secrets

ITERATIONS = 600_000


def supported_password_hash(encoded: str) -> bool:
    try:
        algorithm, rounds, salt, digest = encoded.split("$")
        return (
            algorithm == "pbkdf2_sha256"
            and ITERATIONS <= int(rounds) <= 2_000_000
            and len(base64.b64decode(salt, validate=True)) >= 16
            and len(base64.b64decode(digest, validate=True)) == 32
        )
    except (ValueError, TypeError, AttributeError):
        return False


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(32)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return "$".join(
        [
            "pbkdf2_sha256",
            str(ITERATIONS),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or not ITERATIONS <= int(rounds) <= 2_000_000:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), base64.b64decode(salt, validate=True), int(rounds)
        )
        return hmac.compare_digest(actual, base64.b64decode(expected, validate=True))
    except (ValueError, TypeError):
        return False
