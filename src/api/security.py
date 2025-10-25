from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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