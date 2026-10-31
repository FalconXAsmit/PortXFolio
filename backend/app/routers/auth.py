from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.auth import UserCreate, UserLogin, UserResponse, Token, TokenRefresh
from backend.app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.register_user(user_in)

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    service = AuthService(db)
    login_in = UserLogin(email=form_data.username, password=form_data.password)
    return service.authenticate_user(login_in)

@router.post("/login/json", response_model=Token)
def login_json(login_in: UserLogin, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.authenticate_user(login_in)

@router.post("/refresh", response_model=Token)
def refresh_token(token_in: TokenRefresh, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.refresh_access_token(token_in.refresh_token)

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
