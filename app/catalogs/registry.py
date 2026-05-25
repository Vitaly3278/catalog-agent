"""10 каталогов тестовой версии."""

from pathlib import Path

from app.catalogs.base import CatalogAdapter, CatalogMeta
from app.catalogs.adapters import DemoCatalogAdapter, LiveCatalogAdapter
from app.config import BASE_DIR, get_settings

DEMO_STATIC_DIR = BASE_DIR / "static" / "demo"

# Реальные каталоги (live). В demo_mode URL подменяются на /demo/{id}/
CATALOG_META_LIST: list[CatalogMeta] = [
    CatalogMeta("yell", "Yell.ru", "https://www.yell.ru/history/add/", email_sender_hint="yell"),
    CatalogMeta("orgpage", "OrgPage.ru", "https://www.orgpage.ru/add/", email_sender_hint="orgpage"),
    CatalogMeta("spravker", "Spravker.ru", "https://spravker.ru/add-company", email_sender_hint="spravker"),
    CatalogMeta("allbiz", "AllBiz.ru", "https://www.allbiz.ru/add/", email_sender_hint="allbiz"),
    CatalogMeta("list_org", "List-Org.com", "https://www.list-org.com/?mode=add", email_sender_hint="list-org"),
    CatalogMeta("bizorg", "BizOrg.su", "https://www.bizorg.su/add_firm", email_sender_hint="bizorg"),
    CatalogMeta("ruscatalog", "RusCatalog.org", "https://www.ruscatalog.org/add/", email_sender_hint="ruscatalog"),
    CatalogMeta("tiuru", "Tiuru.ru", "https://tiuru.ru/add-company.html", email_sender_hint="tiuru"),
    CatalogMeta("firmika", "Firmika.ru", "https://firmika.ru/company/add", email_sender_hint="firmika"),
    CatalogMeta("catalog10", "Справочник №10", "https://example.com/add", email_sender_hint="catalog"),
]


def resolve_register_url(meta: CatalogMeta) -> str:
    settings = get_settings()
    if settings.demo_mode:
        reg = DEMO_STATIC_DIR / "register.html"
        return reg.as_uri() + f"?catalog={meta.id}&name={meta.name.replace(' ', '+')}"
    return meta.register_url


def build_adapter(catalog_id: str, company: dict, site_email: str) -> CatalogAdapter | None:
    meta = next((m for m in CATALOG_META_LIST if m.id == catalog_id), None)
    if not meta:
        return None
    settings = get_settings()
    if settings.demo_mode:
        demo_meta = CatalogMeta(
            id=meta.id,
            name=meta.name,
            register_url=resolve_register_url(meta),
            email_sender_hint=meta.email_sender_hint,
        )
        return DemoCatalogAdapter(demo_meta, company, site_email, demo_base_url=settings.app_base_url)
    return LiveCatalogAdapter(meta, company, site_email)


def get_all_catalogs() -> list[CatalogMeta]:
    return CATALOG_META_LIST


def list_catalog_ids() -> list[str]:
    return [m.id for m in CATALOG_META_LIST]
