from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from database.database import Base, engine
import database.models

from routes.linkedin import router as linkedin_router
from routes.auth import router as auth_router

print("1 - app.py started")

Base.metadata.create_all(bind=engine)

print("2 - Database initialized")

app = FastAPI(title="Recruiter Toolkit AI - LinkedIn")

print("3 - FastAPI app created")

# ---------------------------------------------------
# Routers
# ---------------------------------------------------

app.include_router(auth_router)
app.include_router(linkedin_router)

# ---------------------------------------------------
# Static Files
# ---------------------------------------------------

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(directory="templates")

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
        request=request,
        name="home.html"
    )


@app.get("/tools")
def tools(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="tools.html"
    )


@app.get("/login")
def login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )


@app.get("/register")
def register_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="register.html"
    )
