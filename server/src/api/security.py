from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from server.src.api.utils import verify_password
from server.src.models.user import User
from sqlmodel import Session, select
from typing import Optional

from src.db import get_session
from src.models import Project

def get_project_from_secret_key(
    session: Session = Depends(get_session),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=True))
) -> Project:
    
    if not auth or auth.scheme != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid authorization scheme"
        )
        
    project = session.exec(
        select(Project).where(Project.secret_api_key == auth.credentials)
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid Secret API Key"
        )
        
    return project

def get_project_for_tracking(
    request: Request,
    session: Session = Depends(get_session),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Project:
    
    project = None
    
    if x_api_key:
        # 1. Try finding by Public API Key (for client-side)
        project = session.exec(
            select(Project).where(Project.public_api_key == x_api_key)
        ).first()
        
        # --- DOMAIN WHITELISTING SECURITY CHECK ---
        if project and project.allowed_origins:
            origin = request.headers.get("origin")
            if not origin or origin not in project.allowed_origins:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Origin not allowed"
                )
        
    elif auth and auth.scheme == "Bearer":
        # 2. Try finding by Secret API Key (for server-side)
        project = session.exec(
            select(Project).where(Project.secret_api_key == auth.credentials)
        ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid API Key or Token"
        )
        
    return project

async def get_current_user(
    session: Session = Depends(get_session),
    x_user_email: str = Header(...),
    x_user_password: str = Header(...)     
) -> User:
    user = session.exec(select(User).where(User.email == x_user_email)).first()
    if not user or not verify_password(x_user_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials in headers"
        )
    return user