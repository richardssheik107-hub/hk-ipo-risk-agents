"""Gold-independent discovery of official HKEX prospectus language editions.

The resolver uses only governed issuer/listing identity and HKEX title-search
metadata.  It never receives evaluator anchors, case-specific rules, or page
numbers.  Downloaded PDFs remain local; callers persist only safe provenance
metadata and content hashes.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


HKEX_ORIGIN = "https://www1.hkexnews.hk"
ACTIVE_STOCK_INDEX = f"{HKEX_ORIGIN}/ncms/script/eds/activestock_sehk_e.json"
INACTIVE_STOCK_INDEX = f"{HKEX_ORIGIN}/ncms/script/eds/inactivestock_sehk_e.json"
TITLE_SEARCH_ENDPOINT = f"{HKEX_ORIGIN}/search/titleSearchServlet.do"
SOURCE_AUTHORITY = "Hong Kong Exchanges and Clearing Limited / HKEXnews"

_ENGLISH_TITLES = (
    "prospectus",
    "global offering",
    "share offer",
    "listing by way of introduction",
)
_CHINESE_TITLES = ("招股章程", "全球發售", "股份發售", "介紹上市")
_LISTING_DOCUMENT_PREFIXES = ("listing documents", "上市文件")
_PDF_SIZE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(KB|MB|GB)\s*$", re.IGNORECASE)


class HKEXSourceError(ValueError):
    """Raised when official source discovery cannot prove a safe identity."""


@dataclass(frozen=True, slots=True)
class HKEXStockIdentity:
    stock_id: int
    stock_code: str
    stock_name: str


@dataclass(frozen=True, slots=True)
class HKEXDocument:
    stock_code: str
    stock_name: str
    language: str
    release_time: datetime
    title: str
    category: str
    file_url: str
    file_info: str
    news_id: str

    @property
    def release_date(self) -> date:
        return self.release_time.date()


@dataclass(frozen=True, slots=True)
class HKEXEditionSet:
    listing_identity: str
    filing_identity: str
    stock_identity: HKEXStockIdentity
    disclosure_date: date
    english: HKEXDocument | None
    chinese: HKEXDocument | None
    relationship_confidence: str

    @property
    def bilingual(self) -> bool:
        return self.english is not None and self.chinese is not None


def normalize_hkex_stock_code(value: object) -> str:
    token = str(value or "").strip().upper().removesuffix(".HK")
    digits = "".join(character for character in token if character.isdigit())
    if not digits:
        raise HKEXSourceError("stock code has no digits")
    return digits.zfill(5)


def parse_active_stock_index(payload: bytes) -> dict[str, HKEXStockIdentity]:
    candidates = parse_stock_index_candidates(payload)
    try:
        return {code: identities[0] for code, identities in candidates.items()}
    except IndexError as exc:  # pragma: no cover - guarded by parser construction
        raise HKEXSourceError("HKEX active-stock index contains an empty group") from exc


def parse_stock_index_candidates(
    payload: bytes,
) -> dict[str, tuple[HKEXStockIdentity, ...]]:
    """Parse current or delisted securities without conflating reused codes."""

    try:
        rows = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HKEXSourceError("HKEX stock index is not valid JSON") from exc
    grouped: dict[str, list[HKEXStockIdentity]] = {}
    for row in rows:
        code = normalize_hkex_stock_code(row.get("c"))
        identity = HKEXStockIdentity(
            stock_id=int(row["i"]),
            stock_code=code,
            stock_name=str(row.get("n") or "").strip(),
        )
        grouped.setdefault(code, []).append(identity)
    return {
        code: tuple(sorted(identities, key=lambda item: item.stock_id))
        for code, identities in grouped.items()
    }


def parse_title_search_response(payload: bytes, *, language: str) -> tuple[HKEXDocument, ...]:
    try:
        envelope = json.loads(payload.decode("utf-8-sig"))
        rows = json.loads(envelope["result"])
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise HKEXSourceError("HKEX title-search response is invalid") from exc
    documents: list[HKEXDocument] = []
    for row in rows:
        link = str(row.get("FILE_LINK") or "").strip()
        if not link.lower().endswith(".pdf"):
            continue
        documents.append(
            HKEXDocument(
                stock_code=normalize_hkex_stock_code(row.get("STOCK_CODE")),
                stock_name=str(row.get("STOCK_NAME") or "").strip(),
                language=language,
                release_time=datetime.strptime(str(row["DATE_TIME"]), "%d/%m/%Y %H:%M"),
                title=" ".join(str(row.get("TITLE") or "").split()),
                category=" ".join(str(row.get("LONG_TEXT") or "").split()),
                file_url=link if link.startswith("http") else f"{HKEX_ORIGIN}{link}",
                file_info=str(row.get("FILE_INFO") or "").strip(),
                news_id=str(row.get("NEWS_ID") or "").strip(),
            )
        )
    return tuple(documents)


def _looks_like_prospectus(document: HKEXDocument) -> bool:
    category = document.category.casefold()
    if not any(category.startswith(prefix) for prefix in _LISTING_DOCUMENT_PREFIXES):
        return False
    title = document.title.casefold()
    tokens = _ENGLISH_TITLES if document.language == "en" else _CHINESE_TITLES
    return any(token in title for token in tokens)


def _size_bytes_hint(file_info: str) -> int:
    match = _PDF_SIZE.match(file_info)
    if not match:
        return 0
    multiplier = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}[match.group(2).upper()]
    return int(float(match.group(1)) * multiplier)


def select_official_prospectus(
    documents: Iterable[HKEXDocument], *, disclosure_date: date
) -> HKEXDocument | None:
    """Select the official prospectus, not a form or formal notice.

    HKEX's official document category is the hard gate.  Within that category,
    the closest release date and largest PDF are generic tie-breakers.
    """

    candidates = [document for document in documents if _looks_like_prospectus(document)]
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            abs((item.release_date - disclosure_date).days),
            -_size_bytes_hint(item.file_info),
            item.release_time,
            item.file_url,
        )
    )
    return candidates[0]


def edition_relationship_confidence(
    english: HKEXDocument | None,
    chinese: HKEXDocument | None,
    *,
    disclosure_date: date,
) -> str:
    if english is None or chinese is None:
        return "single_language_only"
    if (
        english.stock_code == chinese.stock_code
        and english.release_date == chinese.release_date == disclosure_date
        and _looks_like_prospectus(english)
        and _looks_like_prospectus(chinese)
    ):
        return "high"
    if english.stock_code == chinese.stock_code and english.release_date == chinese.release_date:
        return "medium"
    return "low"


class HKEXEditionResolver:
    """Read-only client for HKEX's public official title-search sources."""

    def __init__(
        self,
        *,
        fetch: Callable[[str], bytes] | None = None,
        user_agent: str = "hk-ipo-risk-agents/source-edition-audit",
    ) -> None:
        self.user_agent = user_agent
        self._fetch_override = fetch
        self._stock_index: dict[str, HKEXStockIdentity] | None = None
        self._inactive_stock_index: dict[
            str, tuple[HKEXStockIdentity, ...]
        ] | None = None

    def _fetch(self, url: str) -> bytes:
        if self._fetch_override is not None:
            return self._fetch_override(url)
        request = Request(url, headers={"User-Agent": self.user_agent})
        with urlopen(request, timeout=45) as response:  # noqa: S310 - fixed official origin
            return response.read()

    def stock_index(self) -> dict[str, HKEXStockIdentity]:
        if self._stock_index is None:
            self._stock_index = parse_active_stock_index(self._fetch(ACTIVE_STOCK_INDEX))
        return self._stock_index

    def inactive_stock_index(self) -> dict[str, tuple[HKEXStockIdentity, ...]]:
        if self._inactive_stock_index is None:
            self._inactive_stock_index = parse_stock_index_candidates(
                self._fetch(INACTIVE_STOCK_INDEX)
            )
        return self._inactive_stock_index

    def _title_search(
        self,
        identity: HKEXStockIdentity,
        *,
        language: str,
        start: date,
        end: date,
    ) -> tuple[HKEXDocument, ...]:
        params = {
            "sortDir": "0",
            "sortByOptions": "DateTime",
            "category": "0",
            "market": "SEHK",
            "stockId": str(identity.stock_id),
            "documentType": "-1",
            "fromDate": start.strftime("%Y%m%d"),
            "toDate": end.strftime("%Y%m%d"),
            "title": "",
            "searchType": "0",
            "t1code": "-2",
            "t2Gcode": "-2",
            "t2code": "-2",
            "rowRange": "100",
            # HKEX accepts ``ZH`` for Traditional Chinese and reports ``C``
            # in the response envelope. Passing ``C`` silently falls back to
            # English, so keep the request token explicit here.
            "lang": "E" if language == "en" else "ZH",
        }
        payload = self._fetch(f"{TITLE_SEARCH_ENDPOINT}?{urlencode(params)}")
        return parse_title_search_response(payload, language=language)

    def discover(
        self,
        *,
        stock_code: str,
        disclosure_date: date,
        window_days: int = 2,
    ) -> HKEXEditionSet:
        code = normalize_hkex_stock_code(stock_code)
        start = disclosure_date - timedelta(days=window_days)
        end = disclosure_date + timedelta(days=window_days)
        active_identity = self.stock_index().get(code)
        identities = (active_identity,) if active_identity is not None else ()
        english = None
        chinese = None
        selected_identity = active_identity
        for identity in identities:
            english = select_official_prospectus(
                self._title_search(identity, language="en", start=start, end=end),
                disclosure_date=disclosure_date,
            )
            chinese = select_official_prospectus(
                self._title_search(identity, language="zh-Hant", start=start, end=end),
                disclosure_date=disclosure_date,
            )
        if english is None or chinese is None:
            for identity in self.inactive_stock_index().get(code, ()):
                candidate_english = select_official_prospectus(
                    self._title_search(identity, language="en", start=start, end=end),
                    disclosure_date=disclosure_date,
                )
                candidate_chinese = select_official_prospectus(
                    self._title_search(identity, language="zh-Hant", start=start, end=end),
                    disclosure_date=disclosure_date,
                )
                candidate_score = int(candidate_english is not None) + int(
                    candidate_chinese is not None
                )
                selected_score = int(english is not None) + int(chinese is not None)
                if candidate_score > selected_score:
                    selected_identity = identity
                    english = candidate_english
                    chinese = candidate_chinese
                if english is not None and chinese is not None:
                    break
        if selected_identity is None:
            raise HKEXSourceError(f"stock code absent from HKEX stock indexes: {code}")
        listing_identity = f"SEHK:{code}:{disclosure_date.isoformat()}:prospectus"
        filing_identity = (
            f"HKEXNEWS:{code}:{disclosure_date.isoformat()}:listing_documents:prospectus"
        )
        return HKEXEditionSet(
            listing_identity=listing_identity,
            filing_identity=filing_identity,
            stock_identity=selected_identity,
            disclosure_date=disclosure_date,
            english=english,
            chinese=chinese,
            relationship_confidence=edition_relationship_confidence(
                english, chinese, disclosure_date=disclosure_date
            ),
        )


def download_official_pdf(url: str, *, fetch: Callable[[str], bytes] | None = None) -> bytes:
    if not url.startswith(f"{HKEX_ORIGIN}/listedco/"):
        raise HKEXSourceError("refusing non-HKEX official PDF URL")
    if fetch is None:
        request = Request(url, headers={"User-Agent": "hk-ipo-risk-agents/source-edition-audit"})
        with urlopen(request, timeout=90) as response:  # noqa: S310 - fixed official origin
            payload = response.read()
    else:
        payload = fetch(url)
    if not payload.startswith(b"%PDF-"):
        raise HKEXSourceError("official document response is not a PDF")
    return payload


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
