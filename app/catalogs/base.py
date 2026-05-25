"""Базовый адаптер каталога для Playwright."""

import json
import secrets
import string
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Page


def generate_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@dataclass
class CatalogMeta:
    id: str
    name: str
    register_url: str
    profile_url_template: str = ""
    email_sender_hint: str = ""
    email_subject_hint: str = ""
    notes: str = ""


@dataclass
class RegistrationResult:
    success: bool
    login: str = ""
    password: str = ""
    profile_url: str = ""
    backlink_url: str = ""
    error: str = ""
    log: list[str] = field(default_factory=list)

    def log_json(self) -> str:
        return json.dumps(self.log, ensure_ascii=False)


class CatalogAdapter(ABC):
    def __init__(self, meta: CatalogMeta, company: dict, site_email: str):
        self.meta = meta
        self.company = company
        self.site_email = site_email
        self.password = generate_password()
        self.log: list[str] = []

    def _log(self, msg: str) -> None:
        self.log.append(msg)

    @abstractmethod
    async def register(
        self, page: Page, verification_code: str | None
    ) -> RegistrationResult:
        ...

    async def fill_profile(self, page: Page) -> None:
        """Дополнительное заполнение карточки после регистрации."""
        pass

    async def safe_fill(self, page: Page, selector: str, value: str) -> bool:
        try:
            loc = page.locator(selector).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.fill(value)
                return True
        except Exception:
            pass
        return False

    async def safe_click(self, page: Page, selector: str) -> bool:
        try:
            loc = page.locator(selector).first
            if await loc.count() > 0:
                await loc.click(timeout=5000)
                return True
        except Exception:
            pass
        return False

    def company_field(self, *keys: str, default: str = "") -> str:
        for k in keys:
            v = self.company.get(k)
            if v:
                return str(v)
        return default
