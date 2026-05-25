"""Адаптеры Playwright для каталогов."""

from urllib.parse import urljoin

from playwright.async_api import Page

from app.catalogs.base import CatalogAdapter, CatalogMeta, RegistrationResult
class LiveCatalogAdapter(CatalogAdapter):
    """Универсальный сценарий для реальных каталогов."""

    def __init__(self, meta: CatalogMeta, company: dict, site_email: str):
        super().__init__(meta, company, site_email)

    async def register(
        self, page: Page, verification_code: str | None
    ) -> RegistrationResult:
        name = self.company_field("name")
        desc = self.company_field("description")
        url = self.company_field("url")
        phone = self.company_field("phone")

        self._log(f"Открываю {self.meta.register_url}")
        await page.goto(self.meta.register_url, wait_until="domcontentloaded", timeout=60000)

        if not verification_code:
            await self._fill_registration_form(page, name, desc, url, phone)
            await page.wait_for_timeout(3000)
            if await self._page_needs_code(page):
                return RegistrationResult(
                    success=False,
                    error="ожидание кода из почты",
                    log=self.log,
                )

        if verification_code:
            await self._submit_verification(page, verification_code)

        await self.fill_profile(page)
        return RegistrationResult(
            success=True,
            login=self.site_email,
            password=self.password,
            profile_url=page.url,
            backlink_url=url,
            log=self.log,
        )

    async def _page_needs_code(self, page: Page) -> bool:
        indicators = ["код", "подтвержд", "verify", "confirm"]
        text = (await page.content()).lower()
        return any(i in text for i in indicators)

    async def _fill_registration_form(
        self, page: Page, name: str, desc: str, url: str, phone: str
    ) -> None:
        for sel in (
            'input[type="email"]',
            'input[name*="email" i]',
            'input[id*="email" i]',
        ):
            if await self.safe_fill(page, sel, self.site_email):
                self._log("Email заполнен")
                break
        for sel in ('input[type="password"]', 'input[name*="pass" i]'):
            if await self.safe_fill(page, sel, self.password):
                self._log("Пароль задан")
                break
        mapping = [
            ('input[name*="company" i], input[name*="name" i]', name),
            ('textarea', desc),
            ('input[name*="site" i], input[name*="url" i]', url),
            ('input[name*="phone" i], input[type="tel"]', phone),
        ]
        for sel, val in mapping:
            if val and await self.safe_fill(page, sel, val):
                self._log(f"Поле {sel}")
        for sel in (
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Регистрация")',
            'button:has-text("Зарегистрироваться")',
            'button:has-text("Добавить")',
        ):
            if await self.safe_click(page, sel):
                self._log("Форма отправлена")
                break

    async def _submit_verification(self, page: Page, code: str) -> None:
        for sel in (
            'input[name*="code" i]',
            'input[name*="confirm" i]',
            'input[placeholder*="код" i]',
        ):
            if await self.safe_fill(page, sel, code):
                self._log("Код введён")
                await self.safe_click(page, 'button[type="submit"]')
                await page.wait_for_timeout(2000)
                return

    async def fill_profile(self, page: Page) -> None:
        desc = self.company_field("description")
        if desc:
            await self.safe_fill(page, "textarea", desc)
        self._log("Доп. заполнение профиля")


class DemoCatalogAdapter(CatalogAdapter):
    """Локальный каталог /demo/{id} — полный цикл."""

    def __init__(
        self,
        meta: CatalogMeta,
        company: dict,
        site_email: str,
        demo_base_url: str = "http://127.0.0.1:8000",
    ):
        super().__init__(meta, company, site_email)
        self.demo_base_url = demo_base_url.rstrip("/")

    @property
    def register_url(self) -> str:
        path = self.meta.register_url
        if path.startswith("http"):
            return path
        return urljoin(self.demo_base_url + "/", path.lstrip("/"))

    async def register(
        self, page: Page, verification_code: str | None
    ) -> RegistrationResult:
        name = self.company_field("name", default="Компания")
        desc = self.company_field("description", default="Описание компании")
        url = self.company_field("url")
        phone = self.company_field("phone", default="+79000000000")

        self._log(f"Demo: {self.register_url}")
        await page.goto(self.register_url, wait_until="networkidle")

        await page.fill("#email", self.site_email)
        await page.fill("#password", self.password)
        await page.fill("#company", name)
        await page.fill("#website", url)
        await page.click("#btn-register")
        await page.wait_for_url("**/verify.html**", timeout=15000)

        code = verification_code
        if not code:
            demo_el = page.locator("#demo-code")
            if await demo_el.count():
                code = (await demo_el.inner_text()).strip()

        if not code:
            return RegistrationResult(
                success=False,
                error="Нет кода (страница #demo-code или IMAP)",
                log=self.log,
            )

        await page.fill("#code", code)
        await page.click("#btn-verify")
        await page.wait_for_url("**/profile.html**", timeout=15000)

        await page.fill("#description", desc)
        await page.fill("#phone", phone)
        services = self.company.get("services") or []
        if services:
            await page.fill("#services", ", ".join(services[:10]))
        await page.click("#btn-save-profile")

        backlink = ""
        bl = page.locator("#backlink-preview")
        if await bl.count():
            backlink = (await bl.inner_text()).strip()

        self._log(f"Готово, ссылка: {backlink}")
        return RegistrationResult(
            success=True,
            login=self.site_email,
            password=self.password,
            profile_url=page.url,
            backlink_url=backlink or url,
            log=self.log,
        )
