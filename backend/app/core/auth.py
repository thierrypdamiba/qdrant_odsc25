"""Mock authentication with 3 users and different permissions"""
from typing import Optional, List
from pydantic import BaseModel


class UserPermissions(BaseModel):
    """User permissions model"""
    can_search_local: bool
    can_search_internet: bool
    can_access_classified: bool
    can_upload_documents: bool


class User(BaseModel):
    """User model"""
    user_id: str
    username: str
    role: str
    permissions: UserPermissions


# Mock users with different permission levels
MOCK_USERS = {
    "admin": User(
        user_id="user_1",
        username="admin",
        role="admin",
        permissions=UserPermissions(
            can_search_local=True,
            can_search_internet=True,
            can_access_classified=True,
            can_upload_documents=True
        )
    ),
    "local_user": User(
        user_id="user_2",
        username="local_user",
        role="local_only",
        permissions=UserPermissions(
            can_search_local=True,
            can_search_internet=False,
            can_access_classified=False,
            can_upload_documents=False
        )
    ),
    "hybrid_user": User(
        user_id="user_3",
        username="hybrid_user",
        role="hybrid",
        permissions=UserPermissions(
            can_search_local=True,
            can_search_internet=True,
            can_access_classified=False,
            can_upload_documents=False
        )
    )
}


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Mock authentication - accepts any password for valid usernames"""
    return MOCK_USERS.get(username)


def get_user_by_token(token: str) -> Optional[User]:
    """Mock token validation - token is just the username"""
    return MOCK_USERS.get(token)


