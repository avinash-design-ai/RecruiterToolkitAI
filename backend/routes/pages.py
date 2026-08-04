from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/")
def index():
    return RedirectResponse("/home")


@router.get("/home")
def home(request: Request):
    return templates.TemplateResponse(
        request,
        "home.html",
        {}
    )


@router.get("/about")
def about(request: Request):
    return templates.TemplateResponse(
        request,
        "about.html",
        {}
    )


@router.get("/tools")
def tools(request: Request):
    return templates.TemplateResponse(
        request,
        "tools.html",
        {}
    )


@router.get("/contact")
def contact(request: Request):
    return templates.TemplateResponse(
        request,
        "contact.html",
        {}
    )


@router.get("/tools/wage")
def wage_page(request: Request):
    return templates.TemplateResponse(
        request,
        "wage.html",
        {}
    )


@router.get("/tools/resume")
def resume_page(request: Request):
    return templates.TemplateResponse(
        request,
        "resume_formatter.html",
        {}
    )
