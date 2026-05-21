import os
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.auth import oauth
from app.database import database, users

router = APIRouter()

ADMIN_EMAILS = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}
APP_URL = os.getenv("APP_URL", "http://localhost:8000")


async def get_or_create_user(email: str, name: str, picture: str | None) -> dict:
    row = await database.fetch_one(users.select().where(users.c.email == email))
    if row:
        return dict(row)
    is_admin = email.lower() in ADMIN_EMAILS
    user_id = await database.execute(
        users.insert().values(email=email, name=name, picture=picture, is_admin=is_admin)
    )
    return {"id": user_id, "email": email, "name": name, "picture": picture, "is_admin": is_admin}


@router.get("/login")
async def login(request: Request):
    google_available = bool(os.getenv("GOOGLE_CLIENT_ID"))
    microsoft_available = bool(os.getenv("MICROSOFT_CLIENT_ID"))

    if google_available and not microsoft_available:
        redirect_uri = f"{APP_URL}/auth/google/callback"
        return await oauth.google.authorize_redirect(request, redirect_uri)
    if microsoft_available and not google_available:
        redirect_uri = f"{APP_URL}/auth/microsoft/callback"
        return await oauth.microsoft.authorize_redirect(request, redirect_uri)

    # Begge tilgængelige – vis login-side
    from fastapi.responses import HTMLResponse
    return HTMLResponse("""
    <html><head><title>Log ind</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head><body class="flex items-center justify-center min-h-screen bg-gray-50">
    <div class="bg-white p-8 rounded-xl shadow text-center space-y-4">
      <h1 class="text-2xl font-bold text-gray-800">Log ind</h1>
      <a href="/auth/google" class="block w-full bg-red-500 text-white py-2 rounded hover:bg-red-600">Log ind med Google</a>
      <a href="/auth/microsoft" class="block w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">Log ind med Microsoft</a>
    </div></body></html>
    """)


@router.get("/auth/google")
async def google_login(request: Request):
    redirect_uri = f"{APP_URL}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback")
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo") or await oauth.google.userinfo(token=token)
    user = await get_or_create_user(userinfo["email"], userinfo.get("name", ""), userinfo.get("picture"))
    request.session["user"] = {"id": user["id"], "email": user["email"], "name": user["name"],
                                "picture": user.get("picture"), "is_admin": user["is_admin"]}
    return RedirectResponse("/")


@router.get("/auth/microsoft")
async def microsoft_login(request: Request):
    redirect_uri = f"{APP_URL}/auth/microsoft/callback"
    return await oauth.microsoft.authorize_redirect(request, redirect_uri)


@router.get("/auth/microsoft/callback")
async def microsoft_callback(request: Request):
    token = await oauth.microsoft.authorize_access_token(request)
    userinfo = token.get("userinfo") or await oauth.microsoft.userinfo(token=token)
    email = userinfo.get("email") or userinfo.get("preferred_username", "")
    user = await get_or_create_user(email, userinfo.get("name", ""), None)
    request.session["user"] = {"id": user["id"], "email": user["email"], "name": user["name"],
                                "picture": None, "is_admin": user["is_admin"]}
    return RedirectResponse("/")


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")
