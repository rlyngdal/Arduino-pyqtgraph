import os
import json
import uuid
import aiofiles
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from app.database import database, claims, claim_files, users

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".heic", ".webp"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def require_login(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user


def require_admin(request: Request) -> dict:
    user = require_login(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Kun for kasserer/admin")
    return user


async def save_file(file: UploadFile, claim_id: int, file_type: str) -> tuple[str, str]:
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Filtype ikke tilladt: {ext}")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Fil er for stor (max 20 MB)")

    folder = UPLOAD_DIR / str(datetime.now().year) / str(datetime.now().month).zfill(2) / str(claim_id) / file_type
    folder.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    path = folder / safe_name
    async with aiofiles.open(path, "wb") as f:
        await f.write(content)
    return str(path), file.filename


@router.get("/")
async def index(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login")
    if user.get("is_admin"):
        return RedirectResponse("/admin")
    return RedirectResponse("/mine-udgifter")


@router.get("/mine-udgifter")
async def my_claims(request: Request):
    user = require_login(request)
    rows = await database.fetch_all(
        claims.select().where(claims.c.user_id == user["id"]).order_by(claims.c.submitted_at.desc())
    )
    return templates.TemplateResponse("my_claims.html", {"request": request, "user": user, "claims": rows})


@router.get("/indsend-udgift")
async def new_claim_form(request: Request):
    user = require_login(request)
    return templates.TemplateResponse("new_claim.html", {"request": request, "user": user})


@router.post("/indsend-udgift")
async def submit_claim(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    amount: float = Form(...),
    participants: str = Form(""),
    is_race: bool = Form(False),
    receipts: list[UploadFile] = File(default=[]),
    proofs: list[UploadFile] = File(default=[]),
):
    user = require_login(request)

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Beløb skal være positivt")
    if not any(f.filename for f in receipts):
        raise HTTPException(status_code=400, detail="Mindst én kvittering er påkrævet")
    if is_race and not any(f.filename for f in proofs):
        raise HTTPException(status_code=400, detail="Gennemførelsesbewis er påkrævet for løb")

    participants_list = [p.strip() for p in participants.split("\n") if p.strip()]
    claim_id = await database.execute(
        claims.insert().values(
            user_id=user["id"],
            title=title,
            description=description,
            amount=amount,
            participants=json.dumps(participants_list, ensure_ascii=False),
            is_race=is_race,
            status="pending",
        )
    )

    for f in receipts:
        if f.filename:
            path, orig = await save_file(f, claim_id, "kvittering")
            await database.execute(claim_files.insert().values(
                claim_id=claim_id, file_type="receipt", filename=path, original_name=orig
            ))

    for f in proofs:
        if f.filename:
            path, orig = await save_file(f, claim_id, "bevis")
            await database.execute(claim_files.insert().values(
                claim_id=claim_id, file_type="proof", filename=path, original_name=orig
            ))

    return RedirectResponse("/mine-udgifter?success=1", status_code=303)


@router.get("/udgift/{claim_id}")
async def view_claim(request: Request, claim_id: int):
    user = require_login(request)
    claim = await database.fetch_one(claims.select().where(claims.c.id == claim_id))
    if not claim:
        raise HTTPException(status_code=404)
    if not user.get("is_admin") and claim["user_id"] != user["id"]:
        raise HTTPException(status_code=403)

    files = await database.fetch_all(claim_files.select().where(claim_files.c.claim_id == claim_id))
    owner = await database.fetch_one(users.select().where(users.c.id == claim["user_id"]))
    participants = json.loads(claim["participants"] or "[]")
    return templates.TemplateResponse("claim_detail.html", {
        "request": request, "user": user, "claim": claim,
        "files": files, "owner": owner, "participants": participants,
    })


@router.get("/fil/{file_id}")
async def serve_file(request: Request, file_id: int):
    user = require_login(request)
    row = await database.fetch_one(claim_files.select().where(claim_files.c.id == file_id))
    if not row:
        raise HTTPException(status_code=404)
    claim = await database.fetch_one(claims.select().where(claims.c.id == row["claim_id"]))
    if not user.get("is_admin") and claim["user_id"] != user["id"]:
        raise HTTPException(status_code=403)
    path = Path(row["filename"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Fil ikke fundet")
    return FileResponse(path, filename=row["original_name"])


# ---- Admin routes ----

@router.get("/admin")
async def admin_dashboard(request: Request, status: str = "pending"):
    user = require_admin(request)
    valid_statuses = ["pending", "approved", "rejected", "paid"]
    if status not in valid_statuses:
        status = "pending"
    rows = await database.fetch_all(
        claims.select().where(claims.c.status == status).order_by(claims.c.submitted_at.desc())
    )
    enriched = []
    for row in rows:
        owner = await database.fetch_one(users.select().where(users.c.id == row["user_id"]))
        enriched.append({"claim": row, "owner": owner})
    counts = {}
    for s in valid_statuses:
        counts[s] = await database.fetch_val(
            claims.select().with_only_columns(claims.c.id.count()).where(claims.c.status == s)
        ) or 0
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request, "user": user, "claims": enriched,
        "current_status": status, "counts": counts,
    })


@router.post("/admin/udgift/{claim_id}/godkend")
async def approve_claim(request: Request, claim_id: int, comment: str = Form("")):
    user = require_admin(request)
    await database.execute(
        claims.update().where(claims.c.id == claim_id).values(
            status="approved", admin_comment=comment, reviewed_at=datetime.now()
        )
    )
    return RedirectResponse(f"/udgift/{claim_id}?success=approved", status_code=303)


@router.post("/admin/udgift/{claim_id}/afvis")
async def reject_claim(request: Request, claim_id: int, comment: str = Form(...)):
    user = require_admin(request)
    await database.execute(
        claims.update().where(claims.c.id == claim_id).values(
            status="rejected", admin_comment=comment, reviewed_at=datetime.now()
        )
    )
    return RedirectResponse(f"/udgift/{claim_id}?success=rejected", status_code=303)


@router.post("/admin/udgift/{claim_id}/udbetalt")
async def mark_paid(request: Request, claim_id: int):
    user = require_admin(request)
    await database.execute(
        claims.update().where(claims.c.id == claim_id).values(
            status="paid", paid_at=datetime.now()
        )
    )
    return RedirectResponse(f"/udgift/{claim_id}?success=paid", status_code=303)
