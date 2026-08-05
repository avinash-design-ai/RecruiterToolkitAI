from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from fastapi import UploadFile, File
from fastapi.responses import FileResponse
from pathlib import Path
import shutil

from modules.ResumeFormatterV2.formatter_service import format_resume

from routes.wage import router as wage_router
from routes.excel import router as excel_router
from routes.linkedin import router as linkedin_router
from routes.auth import router as auth_router

from database.database import Base
from database.database import engine

import database.models

print("1 - app.py started")

from fastapi import FastAPI, Request
print("2 - FastAPI imported")

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
print("3 - FastAPI components imported")

from routes.wage import router as wage_router
print("4 - wage router imported")

from routes.excel import router as excel_router
print("5 - excel router imported")

from routes.linkedin import router as linkedin_router
print("6 - linkedin router imported")

from routes.auth import router as auth_router
print("7 - auth router imported")

from database.database import Base, engine
print("8 - database imported")

import database.models
print("9 - models imported")

Base.metadata.create_all(bind=engine)
print("10 - database initialized")

app = FastAPI(title="Recruiter Toolkit AI")
print("11 - FastAPI app created")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Recruiter Toolkit AI")
app.include_router(auth_router)
app.include_router(wage_router)
app.include_router(excel_router)
app.include_router(linkedin_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup():

    print("12 - Startup event")

@app.get("/")
def index():
    return RedirectResponse("/home")


@app.get("/home")
def home(request: Request):
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request
        }
    )


@app.get("/about")
def about(request: Request):
    return templates.TemplateResponse(
        "about.html",
         {
            "request": request
        }
    )


@app.get("/tools")
def tools(request: Request):
    return templates.TemplateResponse(
        "tools.html",
         {
            "request": request
        }
    )


@app.get("/contact")
def contact(request: Request):
    return templates.TemplateResponse(
        "contact.html",
         {
            "request": request
        }
    )

@app.get("/tools/wage")
def wage_page(request: Request):
    return templates.TemplateResponse(
        "wage.html",
         {
            "request": request
        }
    )

@app.get("/tools/resume")
def resume_page(request: Request):

    return templates.TemplateResponse(
        "resume_formatter.html",
        {
            "request": request
        }
    )

@app.post("/api/resume/format")
async def resume_formatter(
    resume: UploadFile = File(...)
):

    # ---------------------------------------
    # Create upload folder
    # ---------------------------------------

    input_folder = Path("uploads/input")

    input_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------
    # Save uploaded resume
    # ---------------------------------------

    input_file = input_folder / resume.filename

    with open(input_file, "wb") as buffer:

        shutil.copyfileobj(
            resume.file,
            buffer
        )

    # ---------------------------------------
    # Format Resume
    # ---------------------------------------

    output_file = format_resume(
        str(input_file)
    )

    # ---------------------------------------
    # Download Result
    # ---------------------------------------

    return FileResponse(
        path=output_file,
        filename=Path(output_file).name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
