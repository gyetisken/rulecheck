"""Download an ordinance and turn it into plain text.

Cities publish their rules as PDFs produced by a word processor, or as web
pages. Both arrive with furniture that is not part of the law: page headers,
line numbers down the margin, navigation menus. This strips the furniture and
leaves the text, because everything downstream reads the text.

Nothing here rewrites the law itself. PDF extraction splits the occasional word
across a space and those are left alone: the quote stored next to each rule has
to match the source, warts included.
"""

from __future__ import annotations

import html
import io
import re
from dataclasses import dataclass

import httpx

BROWSER = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"

_PAGE_FURNITURE = re.compile(
    r"^\s*(page \d+ of \d+|\d{1,2}/\d{1,2}/\d{4}|ordinance no\.?\s*$)", re.IGNORECASE
)


@dataclass(frozen=True)
class Source:
    """One city's ordinance and where to find it.

    `start` and `end` matter more than they look. Some cities publish the rental
    rules as their own chapter; others bury them inside a zoning ordinance of a
    hundred thousand characters, where the rental part is twenty lines. Sending
    the whole document to a model is slow, expensive and invites it to pick up
    requirements that belong to a different use entirely, so the section is cut
    out first and the markers that cut it are recorded here.
    """

    city: str
    url: str
    description: str
    start: str | None = None
    end: str | None = None


def _strip_line_numbers(lines: list[str]) -> list[str]:
    """Drafting software numbers every line and the number lands in the text.

    The numbers run upward through the document, so a trailing number is only
    treated as furniture when it continues the sequence. A trailing '2026' in a
    sentence does not.
    """
    out: list[str] = []
    last = 0
    for line in lines:
        m = re.search(r"\s*(\d{1,3})\s*$", line)
        if m:
            n = int(m.group(1))
            if last < n <= last + 3:
                line, last = line[: m.start()], n
        out.append(line)
    return out


def _from_pdf(payload: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(payload))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _from_html(payload: bytes) -> str:
    text = payload.decode("utf-8", errors="ignore")
    text = re.sub(r"(?is)<(script|style|nav|header|footer).*?</\1>", " ", text)
    text = re.sub(r"(?i)</(p|div|li|h[1-6]|tr)>", "\n", text)
    return html.unescape(re.sub(r"<[^>]+>", " ", text))


def clean(text: str, drop: tuple[str, ...] = ()) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    lines = _strip_line_numbers(lines)
    kept = [
        line.strip()
        for line in lines
        if line.strip()
        and not _PAGE_FURNITURE.match(line)
        and not any(d.lower() in line.lower() for d in drop)
    ]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept))


def _slice(text: str, start: str | None, end: str | None) -> str:
    if start:
        match = re.search(start, text)
        if not match:
            raise ValueError(f"start marker {start!r} not found in the document")
        text = text[match.start() :]
    if end:
        match = re.search(end, text)
        if match:
            text = text[: match.start()]
    return text.strip()


def fetch(source: Source, drop: tuple[str, ...] = ()) -> str:
    response = httpx.get(
        source.url, headers={"User-Agent": BROWSER}, follow_redirects=True, timeout=60
    )
    response.raise_for_status()
    body = response.content
    is_pdf = body[:4] == b"%PDF" or source.url.lower().endswith(".pdf")
    text = clean(_from_pdf(body) if is_pdf else _from_html(body), drop)
    return _slice(text, source.start, source.end)
