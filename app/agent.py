"""Оркестратор: скрапинг → 10 каталогов → БД."""

import json
from datetime import datetime, timezone

from playwright.async_api import async_playwright

from app import db as database
from app.catalogs.base import RegistrationResult
from app.catalogs.registry import build_adapter, get_all_catalogs
from app.config import get_settings
from app.email_imap import wait_for_code
from app.scraper import scrape_company


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def process_site(site_id: int) -> None:
    site = await database.get_site(site_id)
    if not site:
        return

    await database.update_site(site_id, status="scraping")
    try:
        company = await scrape_company(site["url"])
    except Exception:
        from app.scraper import CompanyData

        company = CompanyData(
            url=site["url"],
            name="Компания",
            description="Описание компании с сайта (скрапинг недоступен — проверьте URL и сеть).",
            phone="+79000000000",
            email=site["email"],
        )
    await database.update_site(
        site_id,
        status="ready",
        company_json=json.dumps(company.to_dict(), ensure_ascii=False),
    )

    company_dict = company.to_dict()
    settings = get_settings()

    for meta in get_all_catalogs():
        reg_id = await database.create_registration(site_id, meta.id, meta.name)
        await database.update_registration(reg_id, status="running")

        adapter = build_adapter(meta.id, company_dict, site["email"])
        if not adapter:
            await database.update_registration(
                reg_id,
                status="failed",
                error_message="Нет адаптера",
                finished_at=_now(),
            )
            continue

        result = await _run_one(adapter, meta, site_id, settings)

        await database.update_registration(
            reg_id,
            status="done" if result.success else "failed",
            login=result.login or None,
            password=result.password or None,
            profile_url=result.profile_url or None,
            backlink_url=result.backlink_url or None,
            error_message=result.error or None,
            log_json=result.log_json(),
            finished_at=_now(),
        )

    await database.update_site(site_id, status="completed")


async def _run_one(adapter, meta, site_id: int, settings) -> RegistrationResult:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.playwright_headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ru-RU",
        )
        page = await context.new_page()
        page.set_default_timeout(settings.playwright_timeout_ms)

        try:
            result = await adapter.register(page, verification_code=None)

            if not result.success and result.error == "ожидание кода из почты":
                code = await wait_for_code(
                    catalog_id=meta.id,
                    site_id=site_id,
                    sender_hint=meta.email_sender_hint,
                    subject_hint=meta.email_subject_hint or "",
                )
                if code:
                    result = await adapter.register(page, verification_code=code)

        except Exception as exc:
            result = RegistrationResult(
                success=False,
                error=str(exc),
                log=getattr(adapter, "log", []) + [str(exc)],
            )
        finally:
            await browser.close()

    return result
