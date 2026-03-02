from passlib.hash import bcrypt, pbkdf2_sha256


def hash_password(password: str) -> str:
    try:
        return bcrypt.hash(password)
    except Exception:
        return pbkdf2_sha256.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        if password_hash.startswith("$2"):
            return bcrypt.verify(password, password_hash)
        return pbkdf2_sha256.verify(password, password_hash)
    except Exception:
        return False
