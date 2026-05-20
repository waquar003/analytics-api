from fastapi import Depends, HTTPException, Header, Request, status
from sqlmodel import Session, select
from typing import Optional
from src.db import get_session
from src.models import Project

def get_project_for_tracking(
    request: Request,
    session: Session = Depends(get_session),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Project:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing identification credentials (X-API-Key header)"
        )
    
    project = session.exec(
        select(Project).where(Project.public_api_key == x_api_key)
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Public API Key context"
        )
    
    if project.allowed_origins and "*" not in project.allowed_origins:
        origin = request.headers.get("origin")
        if not origin or origin not in project.allowed_origins:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Origin not allowed for this projetc"
            )
        
    return project