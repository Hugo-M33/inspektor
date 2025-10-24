"""
Authentication utilities for Inspektor.
Handles JWT token creation/validation and password hashing.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid
import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database import User, Session as DBSession
import os

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "720"))  # 30 days default


class AuthError(Exception):
    """Base exception for authentication errors"""
    pass


class InvalidCredentialsError(AuthError):
    """Raised when credentials are invalid"""
    pass


class TokenExpiredError(AuthError):
    """Raised when token has expired"""
    pass


class UserExistsError(AuthError):
    """Raised when trying to create a user that already exists"""
    pass


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, email: str) -> Dict[str, Any]:
    """
    Create a JWT access token for a user.

    Args:
        user_id: User's unique ID
        email: User's email address

    Returns:
        Dictionary containing token and expiration info
    """
    expires_at = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    token_data = {
        "sub": user_id,  # Subject (user ID)
        "email": email,
        "exp": expires_at,  # Expiration time
        "iat": datetime.utcnow(),  # Issued at
        "jti": str(uuid.uuid4()),  # JWT ID (unique token identifier)
    }

    token = jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
        "expires_in": JWT_EXPIRATION_HOURS * 3600,  # Seconds
    }


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string

    Returns:
        Dictionary containing token payload

    Raises:
        TokenExpiredError: If token has expired
        AuthError: If token is invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthError(f"Invalid token: {str(e)}")


def register_user(db: Session, email: str, password: str) -> User:
    """
    Register a new user.

    Args:
        db: Database session
        email: User's email address
        password: Plain text password

    Returns:
        Created User object

    Raises:
        UserExistsError: If user with this email already exists
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise UserExistsError(f"User with email {email} already exists")

    # Create new user
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=hash_password(password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Authenticate a user with email and password.

    Args:
        db: Database session
        email: User's email address
        password: Plain text password

    Returns:
        User object if authentication successful

    Raises:
        InvalidCredentialsError: If credentials are invalid
    """
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise InvalidCredentialsError("Invalid email or password")

    if not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("Invalid email or password")

    return user


def create_session(db: Session, user_id: str, token: str, expires_at: datetime) -> DBSession:
    """
    Create a session record in the database.

    Args:
        db: Database session
        user_id: User's ID
        token: JWT token
        expires_at: Token expiration datetime

    Returns:
        Created Session object
    """
    session = DBSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        token=token,
        expires_at=expires_at,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def validate_session(db: Session, token: str) -> Optional[User]:
    """
    Validate a session token and return the associated user.

    Args:
        db: Database session
        token: JWT token to validate

    Returns:
        User object if session is valid, None otherwise

    Raises:
        TokenExpiredError: If token has expired
        AuthError: If token is invalid
    """
    # Decode and validate JWT
    payload = decode_access_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise AuthError("Invalid token payload")

    # Check if session exists in database
    session = db.query(DBSession).filter(DBSession.token == token).first()

    if not session:
        raise AuthError("Session not found")

    # Check if session has expired
    if session.expires_at < datetime.utcnow():
        # Clean up expired session
        db.delete(session)
        db.commit()
        raise TokenExpiredError("Session has expired")

    # Get user
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise AuthError("User not found")

    return user


def logout_user(db: Session, token: str) -> None:
    """
    Logout a user by deleting their session.

    Args:
        db: Database session
        token: JWT token to invalidate
    """
    session = db.query(DBSession).filter(DBSession.token == token).first()
    if session:
        db.delete(session)
        db.commit()


def cleanup_expired_sessions(db: Session) -> int:
    """
    Clean up expired sessions from the database.

    Args:
        db: Database session

    Returns:
        Number of sessions deleted
    """
    deleted = db.query(DBSession).filter(DBSession.expires_at < datetime.utcnow()).delete()
    db.commit()
    return deleted
