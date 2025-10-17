"""Authentication routes"""
from fastapi import APIRouter, HTTPException, status, Depends
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse
from app.core.auth import authenticate_user, User
from app.core.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Mock login endpoint - returns username as token"""
    user = authenticate_user(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    return LoginResponse(
        access_token=user.username,  # Mock token is just the username
        token_type="bearer",
        user={
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role,
            "permissions": user.permissions.dict()
        }
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.role,
        permissions=current_user.permissions
    )


