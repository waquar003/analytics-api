from fastapi import APIRouter, Depends, HTTPException, status
from server.src.api.utils import hash_password, verify_password
from sqlmodel import Session
from src.db import get_session
from src.models.user import User, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=['Authentication'])

@router.post('/signup', response_model=UserRead, status_code=status.HTTP_201_CREATED)
def signup(
    user_data: UserCreate,
    session: Session = Depends(get_session),    
):
    existing_user = session.query(User).filter(User.email == user_data.email).first()
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

@router.post("/login", response_model=UserRead)
def login(
    user_data: UserCreate, 
    session: Session = Depends(get_session)
):
    user = session.query(User).filter(User.email == user_data.email).first()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    return user