from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError
from werkzeug.security import check_password_hash


_PASSWORD_HASHER = PasswordHasher()


def hash_secret(secret):
    return _PASSWORD_HASHER.hash(secret)


def verify_secret(stored_hash, candidate_secret):
    if not stored_hash:
        return False

    try:
        return _PASSWORD_HASHER.verify(stored_hash, candidate_secret)
    except VerifyMismatchError:
        return False
    except (InvalidHash, VerificationError):
        # Backward compatibility for previously stored Werkzeug hashes.
        return check_password_hash(stored_hash, candidate_secret)


def needs_rehash(stored_hash):
    if not stored_hash:
        return True

    try:
        return _PASSWORD_HASHER.check_needs_rehash(stored_hash)
    except InvalidHash:
        return True
