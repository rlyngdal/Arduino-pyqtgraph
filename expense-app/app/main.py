import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.database import init_db, close_db
from app.routers import auth_routes, claims_routes

SECRET_KEY = os.getenv("SECRET_KEY", "development-secret-change-me")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="Udgiftsrefusion", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session",
    max_age=60 * 60 * 24 * 7,  # 7 dage
    https_only=os.getenv("APP_URL", "").startswith("https"),
    same_site="lax",
)

app.include_router(auth_routes.router)
app.include_router(claims_routes.router)

templates = Jinja2Templates(directory="app/templates")


@app.get("/login")
async def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/")
    google_available = bool(os.getenv("GOOGLE_CLIENT_ID"))
    microsoft_available = bool(os.getenv("MICROSOFT_CLIENT_ID"))
    if google_available and not microsoft_available:
        return RedirectResponse("/auth/google")
    if microsoft_available and not google_available:
        return RedirectResponse("/auth/microsoft")
    return templates.TemplateResponse("login.html", {
        "request": request,
        "google_available": google_available,
        "microsoft_available": microsoft_available,
    })
