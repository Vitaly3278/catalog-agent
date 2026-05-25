"""Получение кодов подтверждения из почты по IMAP."""

import email
import imaplib
import re
from email.header import decode_header

from app.config import get_settings
from app import db as database

CODE_PATTERNS = [
    re.compile(r"\b(\d{4,8})\b"),
    re.compile(r"код[:\s]+(\d{4,8})", re.I),
    re.compile(r"code[:\s]+(\d{4,8})", re.I),
    re.compile(r"verification[:\s]+(\d{4,8})", re.I),
]


def _decode_header_value(raw: str | None) -> str:
    if not raw:
        return ""
    parts = decode_header(raw)
    out = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(chunk)
    return "".join(out)


def _extract_code(text: str) -> str | None:
    for pat in CODE_PATTERNS:
        m = pat.search(text)
        if m:
            code = m.group(1)
            if 4 <= len(code) <= 8:
                return code
    return None


def fetch_verification_code(
    *,
    since_minutes: int = 30,
    sender_contains: str | None = None,
    subject_contains: str | None = None,
) -> str | None:
    settings = get_settings()
    if not settings.imap_user or not settings.imap_password:
        return None

    mail = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
    try:
        mail.login(settings.imap_user, settings.imap_password)
        mail.select(settings.imap_folder)
        _, data = mail.search(None, "ALL")
        ids = data[0].split()
        for num in reversed(ids[-40:]):
            _, msg_data = mail.fetch(num, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            subject = _decode_header_value(msg.get("Subject"))
            from_addr = _decode_header_value(msg.get("From"))

            if sender_contains and sender_contains.lower() not in from_addr.lower():
                continue
            if subject_contains and subject_contains.lower() not in subject.lower():
                continue

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode(errors="replace")
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors="replace")

            full = f"{subject}\n{body}"
            code = _extract_code(full)
            if code:
                return code
    finally:
        try:
            mail.logout()
        except Exception:
            pass
    return None


async def wait_for_code(
    *,
    catalog_id: str,
    site_id: int,
    sender_hint: str = "",
    subject_hint: str = "",
    attempts: int = 12,
    interval_sec: float = 10.0,
) -> str | None:
    import asyncio

    for _ in range(attempts):
        code = await asyncio.to_thread(
            fetch_verification_code,
            sender_contains=sender_hint or None,
            subject_contains=subject_hint or None,
        )
        if code:
            await database.save_email_code(
                code=code,
                from_addr=sender_hint,
                subject=subject_hint,
                raw_snippet=code,
                site_id=site_id,
                catalog_id=catalog_id,
            )
            return code
        await asyncio.sleep(interval_sec)
    return None
