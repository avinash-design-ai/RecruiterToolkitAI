from typing import Optional
from pydantic import BaseModel


class LinkedInRequest(BaseModel):

    company: str

    location: str

    max_profiles: int = 250

    linkedin_email: Optional[str] = None

    linkedin_password: Optional[str] = None
