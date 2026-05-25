import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, HttpUrl

from app import db as database
from app.catalogs.registry import get_all_catalogs
from app.config import BASE_DIR, get_settings
from app.worker import enqueue_site

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# session_id -> verification code for demo catalogs
_demo_codes: dict[str, str] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    await database.init_db()
    yield


app = FastAPI(title="Catalog Agent", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


class AddSiteRequest(BaseModel):
    url: HttpUrl
    email: EmailStr


class SiteResponse(BaseModel):
    id: int
    url: str
    email: str
    status: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/api/catalogs")
async def api_catalogs():
    settings = get_settings()
    return {
        "demo_mode": settings.demo_mode,
        "catalogs": [
            {"id": m.id, "name": m.name, "register_url": m.register_url}
            for m in get_all_catalogs()
        ],
    }


@app.get("/api/sites")
async def api_sites():
    sites = await database.list_sites()
    out = []
    for s in sites:
        regs = await database.get_registrations_for_site(s["id"])
        out.append({**s, "registrations": regs})
    return out


@app.get("/api/registrations")
async def api_registrations():
    return await database.list_all_registrations()


@app.post("/api/sites")
async def api_add_site(body: AddSiteRequest):
    site_id = await database.create_site(str(body.url), body.email)
    await enqueue_site(site_id)
    site = await database.get_site(site_id)
    return {"ok": True, "site": site}


@app.post("/api/sites/{site_id}/retry")
async def api_retry(site_id: int):
    site = await database.get_site(site_id)
    if not site:
        raise HTTPException(404, "Сайт не найден")
    await database.update_site(site_id, status="pending")
    await enqueue_site(site_id)
    return {"ok": True}


# --- Demo catalog pages (10 шт., один шаблон) ---

def _catalog_name(catalog_id: str) -> str:
    for m in get_all_catalogs():
        if m.id == catalog_id:
            return m.name
    return catalog_id


@app.get("/demo/{catalog_id}/register", response_class=HTMLResponse)
async def demo_register(request: Request, catalog_id: str):
    if catalog_id not in [m.id for m in get_all_catalogs()]:
        raise HTTPException(404)
    base = f"/demo/{catalog_id}"
    return templates.TemplateResponse(
        request,
        "demo_register.html",
        {
            "catalog_name": _catalog_name(catalog_id),
            "verify_path": f"{base}/verify",
        },
    )


@app.get("/demo/{catalog_id}/verify", response_class=HTMLResponse)
async def demo_verify(request: Request, catalog_id: str):
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    _demo_codes[catalog_id] = code
    return templates.TemplateResponse(
        request,
        "demo_verify.html",
        {
            "catalog_name": _catalog_name(catalog_id),
            "code": code,
            "profile_path": f"/demo/{catalog_id}/profile",
        },
    )


@app.get("/demo/{catalog_id}/profile", response_class=HTMLResponse)
async def demo_profile(request: Request, catalog_id: str, code: str = ""):
    website = request.query_params.get("website", "https://example.com")
    company = request.query_params.get("company", "Компания")
    backlink = f"{get_settings().app_base_url}/demo/{catalog_id}/company/{company}?site={website}"
    return templates.TemplateResponse(
        request,
        "demo_profile.html",
        {
            "catalog_name": _catalog_name(catalog_id),
            "backlink": backlink,
        },
    )
