import secrets
from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from src.api.utils import create_access_token, hash_password, verify_password
from sqlmodel import Session, select
import redis
import uuid

from src.db import get_session
from src.models.user import User, UserCreate, UserRead
from src.config import settings
from src.limiter import limiter

router = APIRouter(prefix="/auth", tags=['Authentication'])
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

@router.post('/signup', response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def signup(
    request: Request,
    user_data: UserCreate,
    session: Session = Depends(get_session),    
):
    existing_user = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user

@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    user_data: UserCreate, 
    response: Response,
    session: Session = Depends(get_session)
):
    user = session.query(User).filter(User.email == user_data.email).first()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(str(user.id), user.email)

    refresh_token = f"ref_{secrets.token_hex(32)}"
    user.refresh_token = refresh_token
    session.add(user)
    session.commit()

    redis_client.setex(
        name=f"auth_session:{refresh_token}",
        time=settings.REFRESH_TOKEN_TIMEOUT,
        value=str(user.id)
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite=None,
        path="/auth"
    )
    
    return {
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    }

@router.post("/refresh")
@limiter.limit("20/minute")
def refresh_session(
    request: Request,
    session: Session = Depends(get_session)
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing session context")
    
    user_id = redis_client.get(f"auth_session:{refresh_token}")
    if not user_id:
        raise HTTPException(status_code=401, detail="Session has timed out. Relogin required")
    
    user = session.get(User, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or session revoked")
    
    new_access_token = create_access_token(str(user.id), user.email)
    return {"access_token": new_access_token}

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_session)
):
    refresh_token = request.cookies.get('refresh_token')
    if refresh_token:
        redis_client.delete(f"auth_session:{refresh_token}")
        user = session.exec(select(User).where(User.refresh_token == refresh_token)).first()
        if user:
            user.refresh_token = None
            session.add(user)
            session.commit()

    response.delete_cookie(key='refresh_token', path='/auth')
    return {'message': 'Session invalidated'}