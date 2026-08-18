from fastapi import FastAPI, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse

from pathlib import Path
import shutil

from modules.ResumeFormatterV2.formatter_service import format_resume

from routes.wage import router as wage_router
from routes.excel import router as excel_router
from routes.linkedin import router as linkedin_router
from routes.auth import router as auth_router

from database.database import Base, engine
import database.models


print("1 - app.py started")

Base.metadata.create_all(bind=engine)
print("2 - Database initialized")

app = FastAPI(title="Recruiter Toolkit AI")
print("3 - FastAPI app created")


# ---------------------------------------------------
# Routers
# ---------------------------------------------------

app.include_router(auth_router)
app.include_router(wage_router)
app.include_router(excel_router)
app.include_router(linkedin_router)


# ---------------------------------------------------

# Static Files

# ---------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

app.mount(
"/static",
StaticFiles(directory=BASE_DIR / "static"),
name="static"
)

templates = Jinja2Templates(
    directory=BASE_DIR / "templates"
)

# ---------------------------------------------------
# Startup
# ---------------------------------------------------

@app.on_event("startup")
async def startup():

    print("4 - Application startup complete")


# ---------------------------------------------------
# Pages
# ---------------------------------------------------

@app.get("/")
def index():

    return RedirectResponse("/home")


@app.get("/home")
def home(request: Request):

    return templates.TemplateResponse(
        request,
        "home.html",
        {}
    )


@app.get("/about")
def about(request: Request):

    return templates.TemplateResponse(
        request,
        "about.html",
        {}
    )


@app.get("/tools")
def tools(request: Request):

    return templates.TemplateResponse(
        request,
        "tools.html",
        {}
    )


@app.get("/contact")
def contact(request: Request):

    return templates.TemplateResponse(
        request,
        "contact.html",
        {}
    )


@app.get("/tools/wage")
def wage_page(request: Request):

    return templates.TemplateResponse(
        request,
        "wage.html",
        {}
    )


@app.get("/tools/resume")
def resume_page(request: Request):

    return templates.TemplateResponse(
        request,
        "resume_formatter.html",
        {}
    )


# ---------------------------------------------------
# Resume Formatter API
# ---------------------------------------------------

# ---------------------------------------------------
# Resume Formatter API
# ---------------------------------------------------

@app.post("/api/resume/format")
async def resume_formatter(
    request: Request,
    resume: UploadFile = File(...)
):

    input_folder = Path("uploads/input")

    input_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    input_file = input_folder / resume.filename

    with open(input_file, "wb") as buffer:

        shutil.copyfileobj(
            resume.file,
            buffer
        )

    output_file = format_resume(
        str(input_file)
    )

    output_filename = Path(output_file).name

    return templates.TemplateResponse(
        request,
        "resume_result.html",
        {
            "filename": output_filename,
            "download_url": f"/api/resume/download/{output_filename}",
        }
    )


# ---------------------------------------------------
# Resume Formatter Download
# ---------------------------------------------------

@app.get("/api/resume/download/{filename}")
async def download_resume(
    filename: str
):

    output_folder = Path("uploads/output")

    file_path = output_folder / filename

    if not file_path.exists():

        return {
            "error": "Formatted resume not found."
        }

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )
    )

