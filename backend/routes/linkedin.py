import os

from fastapi import APIRouter, Request, Depends
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from services.current_user import get_current_user
from database.models import User
from models.linkedin import LinkedInRequest

from modules.RecruiterToolkit.linkedin_runner import run_linkedin
from automation.search_controller import request_stop

router = APIRouter()

templates = Jinja2Templates(directory="templates")


# ----------------------------------------------------
# LinkedIn Page
# ----------------------------------------------------

@router.get("/tools/linkedin")
def linkedin_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="linkedin.html"
    )


# ----------------------------------------------------
# Run LinkedIn Search
# ----------------------------------------------------

@router.post("/linkedin")
def linkedin_search(

    data: LinkedInRequest,

    current_user: User = Depends(get_current_user)

):

    print("=" * 70)
    print("LINKEDIN ENDPOINT HIT")
    print("=" * 70)

    print("Company :", data.company)
    print("Location:", data.location)
    print("Max     :", data.max_profiles)

    if current_user:
        print("User ID :", current_user.id)
    else:
        print("User    : None")

    if not current_user:

        print("Authentication failed.")

        return {

            "success": False,

            "message": "Please login first."

        }

    try:

        print("Calling run_linkedin()...")

        result = run_linkedin(

            company=data.company,

            location=data.location,

            max_profiles=data.max_profiles,

            profile=str(current_user.id),

            linkedin_email=data.linkedin_email,

            linkedin_password=data.linkedin_password

        )

        print("=" * 70)
        print("run_linkedin() RETURNED")
        print(type(result))
        print(result)
        print("=" * 70)

        return result

    except Exception as ex:

        import traceback

        print("=" * 70)
        print("LINKEDIN EXCEPTION")
        print("=" * 70)

        traceback.print_exc()

        return {

            "success": False,

            "message": str(ex)

        }


# ----------------------------------------------------
# Stop LinkedIn Search
# ----------------------------------------------------

@router.post("/linkedin/stop")
def stop_linkedin():

    request_stop()

    return {

        "success": True,

        "message": "Stop request received."

    }


# ----------------------------------------------------
# Download CSV
# ----------------------------------------------------

@router.get("/linkedin/download/{filename}")
def download_csv(filename: str):

    print("Download requested:", filename)

    file_path = os.path.join(

        "modules",

        "RecruiterToolkit",

        "exports",

        filename

    )

    print("Resolved path:", file_path)

    print("Exists:", os.path.exists(file_path))

    if not os.path.exists(file_path):

        return {

            "success": False,

            "message": "CSV file not found."

        }

    return FileResponse(

        path=file_path,

        filename=filename,

        media_type="text/csv"

    )
