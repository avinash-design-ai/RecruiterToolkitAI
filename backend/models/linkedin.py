from pydantic import BaseModel, EmailStr


class LinkedInRequest(BaseModel):
    company: str
    location: str
    max_profiles: int = 250

    linkedin_email: EmailStr
    linkedin_password: str
