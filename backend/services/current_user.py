from fastapi import Cookie
from fastapi import Depends
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import User


def get_current_user(

    user_id: str | None = Cookie(default=None),

    db: Session = Depends(get_db)

):

    if not user_id:

        return None

    return db.query(User).filter(

        User.id == int(user_id)

    ).first()
