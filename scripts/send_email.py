#!/usr/bin/env python3
"""Send an HTML digest over SMTP STARTTLS. Stdlib only."""

from __future__ import annotations

import os
import re
import smtplib
import sys
from email.message import EmailMessage
from html.parser import HTMLParser
from pathlib import Path


class _HTMLToText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style"}:
            self._skip += 1
        elif tag in {"p", "div", "br", "tr", "h1", "h2", "h3", "h4", "li", "hr"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n[ \t]+", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def html_to_text(html: str) -> str:
    parser = _HTMLToText()
    parser.feed(html)
    parser.close()
    text = parser.text()
    return text or "This email is in HTML. Please view it in an HTML-capable client."


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def parse_recipients(raw: str) -> list[str]:
    recipients = [part.strip() for part in raw.split(",") if part.strip()]
    if not recipients:
        raise SystemExit("No recipients provided")
    email_re = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    bad = [addr for addr in recipients if not email_re.match(addr)]
    if bad:
        raise SystemExit(f"Invalid recipient address(es): {', '.join(bad)}")
    return recipients


def resolve_body_path(raw: str) -> Path:
    root = Path.cwd().resolve()
    path = (root / raw).resolve()
    if not path.is_relative_to(root):
        raise SystemExit(f"body path escapes the working directory: {raw}")
    if not path.is_file():
        raise SystemExit(f"HTML body not found: {path}")
    return path


def main() -> None:
    host = os.environ.get("SMTP_HOST", "mail.infomaniak.com").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ.get("SMTP_USERNAME", "info@gmc-works.com").strip()
    password = require_env("SMTP_PASSWORD")
    mail_from = os.environ.get("SMTP_FROM", "info@gmc-works.com").strip()
    ehlo = os.environ.get("SMTP_EHLO", "gmc-works.com").strip()
    subject = require_env("MAIL_SUBJECT")
    recipients = parse_recipients(require_env("MAIL_RECIPIENTS"))
    body_path = resolve_body_path(os.environ.get("MAIL_BODY_PATH", "digest/latest.html"))

    html = body_path.read_text(encoding="utf-8")
    if not html.strip():
        raise SystemExit(f"HTML body is empty: {body_path}")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(html_to_text(html))
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP(host, port, local_hostname=ehlo, timeout=60) as smtp:
        smtp.ehlo(ehlo)
        smtp.starttls()
        smtp.ehlo(ehlo)
        smtp.login(username, password)
        smtp.send_message(msg)

    print(f"Sent to {len(recipients)} recipient(s): {subject}")


if __name__ == "__main__":
    try:
        main()
    except smtplib.SMTPAuthenticationError as exc:
        print(
            f"SMTP authentication failed: {exc.smtp_code} {exc.smtp_error!r}",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
    except smtplib.SMTPException as exc:
        print(f"SMTP error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
