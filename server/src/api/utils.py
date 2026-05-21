import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from src.config import settings

def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using bcrypt.
    """
    pwd_bytes = password.encode('utf-8')
    
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)

    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a hashed one.
    """
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


JWT_SECRET = settings.JWT_SECRET
ALGORITHM = "HS256"


def create_access_token(user_id: str, email: str) -> str:
    """Generates a stateless JWT access token valid for 15 minutes"""
    expire = datetime.now(timezone.utc) + timedelta(seconds=settings.ACCESS_TOKEN_TIMEOUT)
    payload = {
        "sub": user_id,
        "email": email, 
        "exp": int(expire.timestamp())
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    """Decodes and cryptographically verifies the incoming access token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return {}
    except jwt.PyJWTError:
        return {}
