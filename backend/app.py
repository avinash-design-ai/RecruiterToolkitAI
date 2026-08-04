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

app = FastAPI(title="Recruiter Toolkit AI")

app.include_router(wage_router)
app.include_router(excel_router)
app.include_router(linkedin_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


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
