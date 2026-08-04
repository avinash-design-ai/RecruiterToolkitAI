from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(directory="backend/templates")


@router.get("/tools/resume", response_class=HTMLResponse)
async def resume_page(request: Request):

    return templates.TemplateResponse(
        "resume_formatter.html",
        {
            "request": request
        }
    )
