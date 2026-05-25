"""Парсинг данных компании с сайта для заполнения карточек в каталогах."""

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass
class CompanyData:
    url: str
    name: str = ""
    description: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    logo_url: str = ""
    services: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    og_image: str = ""

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "name": self.name,
            "description": self.description,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "logo_url": self.logo_url,
            "services": self.services,
            "keywords": self.keywords,
            "og_image": self.og_image,
        }


PHONE_RE = re.compile(
    r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def _clean_text(text: str, max_len: int = 2000) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len] if len(text) > max_len else text


def _meta(soup: BeautifulSoup, prop: str) -> str:
    tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
    if tag and tag.get("content"):
        return _clean_text(tag["content"], 500)
    return ""


async def scrape_company(url: str) -> CompanyData:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CatalogAgent/1.0; +https://github.com)"
    }
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=30.0, headers=headers
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text
        base_url = str(resp.url)

    soup = BeautifulSoup(html, "lxml")
    data = CompanyData(url=base_url)

    data.name = (
        _meta(soup, "og:site_name")
        or _meta(soup, "og:title")
        or (soup.title.string.strip() if soup.title and soup.title.string else "")
    )
    data.description = _meta(soup, "og:description") or _meta(soup, "description")
    data.og_image = _meta(soup, "og:image")

    if not data.description:
        for sel in ("main p", "article p", ".about p", "#about p", "p"):
            p = soup.select_one(sel)
            if p and len(p.get_text(strip=True)) > 80:
                data.description = _clean_text(p.get_text())
                break

    for link in soup.find_all("link", rel=lambda x: x and "icon" in x.lower()):
        href = link.get("href")
        if href:
            data.logo_url = urljoin(base_url, href)
            break
    if not data.logo_url and data.og_image:
        data.logo_url = urljoin(base_url, data.og_image)

    text = soup.get_text(" ", strip=True)
    phones = PHONE_RE.findall(text)
    if phones:
        data.phone = phones[0]
    emails = EMAIL_RE.findall(text)
    if emails:
        data.email = emails[0]

    for nav in soup.select("nav a, .menu a, .services a, footer a"):
        t = _clean_text(nav.get_text(), 80)
        if 3 < len(t) < 60 and t.lower() not in ("главная", "контакты", "home"):
            if t not in data.services:
                data.services.append(t)
    data.services = data.services[:15]

    host = urlparse(base_url).netloc.replace("www.", "")
    data.keywords = [w for w in host.split(".") if w not in ("ru", "com", "org")][:5]

    if not data.name:
        data.name = host.split(".")[0].capitalize()

    return data
