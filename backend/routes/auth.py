from fastapi import APIRouter
from fastapi import Depends
from fastapi import Response
from sqlalchemy.orm import Session
from services.current_user import get_current_user
from database.database import get_db
from database.models import User

from models.auth import RegisterRequest, LoginRequest

from services.auth_service import (
    hash_password,
    verify_password
)

router = APIRouter()


# ----------------------------------------------------
# Register
# ----------------------------------------------------

@router.post("/register")
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):

    existing = db.query(User).filter(
        User.email == data.email
    ).first()

    if existing:

        return {
            "success": False,
            "message": "Email already exists."
        }

    user = User(

        full_name=data.full_name,

        email=data.email,

        password_hash=hash_password(
            data.password
        )

    )

    db.add(user)

    db.commit()

    db.refresh(user)

    return {

        "success": True,

        "message": "Registration successful."

    }


# ----------------------------------------------------
# Login
# ----------------------------------------------------

@router.post("/login")
def login(
    data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == data.email
    ).first()

    if not user:

        return {

            "success": False,

            "message": "Invalid email or password."

        }

    if not verify_password(
        data.password,
        user.password_hash
    ):

        return {

            "success": False,

            "message": "Invalid email or password."

        }

    response.set_cookie(

        key="user_id",

        value=str(user.id),

        httponly=True

    )

    return {

        "success": True,

        "message": "Login successful.",

        "user": {

            "id": user.id,

            "name": user.full_name,

            "email": user.email

        }

    }

@router.get("/me")
def me(

    user: User = Depends(get_current_user)

):

    if not user:

        return {

            "success": False,

            "message": "Not logged in."

        }

    return {

        "success": True,

        "id": user.id,

        "name": user.full_name,

        "email": user.email

    }
