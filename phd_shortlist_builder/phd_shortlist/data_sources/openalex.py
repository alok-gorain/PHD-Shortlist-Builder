from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests
import urllib3
from tenacity import retry, stop_after_attempt, wait_exponential

from phd_shortlist.config import RuntimeConfig
from phd_shortlist.data_sources.cache import JsonCache

OPENALEX = "https://api.openalex.org"


@dataclass(frozen=True)
class OpenAlexAuthor:
    id: str
    display_name: str
    works_count: int
    cited_by_count: int
    institution: str | None
    country_code: str | None
    institution_country: str | None
    concepts: list[str]
    raw: dict[str, Any]


class OpenAlexClient:
    """Small deterministic OpenAlex client with file caching."""

    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.cache = JsonCache(config.cache_dir / "openalex")

    def search_authors(self, query: str, country_codes: list[str], per_page: int) -> list[OpenAlexAuthor]:
        authors: dict[str, OpenAlexAuthor] = {}
        params = {
            "search": query,
            "per-page": min(per_page, 200),
            "sort": "cited_by_count:desc",
        }
        data = self._get("/authors", params)
        for row in data.get("results", []):
            if not isinstance(row, dict):
                continue
            author = self._parse_author(row, preferred_country_codes=country_codes)
            if country_codes and author.country_code not in country_codes:
                continue
            if author.institution:
                authors[author.id] = author
        return list(authors.values())

    def author_works(self, author_id: str, per_page: int = 8) -> list[dict[str, Any]]:
        openalex_id = author_id.rsplit("/", 1)[-1]
        params = {
            "filter": f"authorships.author.id:{openalex_id},is_paratext:false",
            "per-page": min(per_page, 50),
            "sort": "cited_by_count:desc",
        }
        return self._get("/works", params).get("results", [])

    def search_authors_from_works(
        self, query: str, country_codes: list[str], per_page: int
    ) -> list[OpenAlexAuthor]:
        params = {
            "search": query,
            "per-page": min(per_page, 200),
            "sort": "cited_by_count:desc",
        }
        data = self._get("/works", params)
        authors: dict[str, OpenAlexAuthor] = {}
        for work in data.get("results", []):
            if not isinstance(work, dict):
                continue
            for authorship in work.get("authorships") or []:
                if not _authorship_has_target_education(authorship, country_codes):
                    continue
                author_stub = authorship.get("author") or {}
                author_id = author_stub.get("id")
                if not author_id or author_id in authors:
                    continue
                author = self.get_author(author_id, country_codes)
                if author and author.country_code in country_codes and author.institution:
                    authors[author.id] = author
                if len(authors) >= per_page:
                    return list(authors.values())
        return list(authors.values())

    def get_author(
        self, author_id: str, preferred_country_codes: list[str] | None = None
    ) -> OpenAlexAuthor | None:
        openalex_id = author_id.rsplit("/", 1)[-1]
        data = self._get(f"/authors/{openalex_id}", {})
        if not isinstance(data, dict) or not data.get("id"):
            return None
        return self._parse_author(data, preferred_country_codes=preferred_country_codes or [])

    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3))
    def _request(self, url: str) -> dict[str, Any]:
        if self.config.insecure_skip_tls_verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(
            url,
            timeout=self.config.request_timeout_seconds,
            verify=not self.config.insecure_skip_tls_verify,
        )
        response.raise_for_status()
        return response.json()

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        clean_params = {key: value for key, value in params.items() if value not in (None, "")}
        if self.config.openalex_mailto:
            clean_params["mailto"] = self.config.openalex_mailto
        url = f"{OPENALEX}{path}?{urlencode(clean_params)}"
        cached = self.cache.get("http", url)
        if cached is not None:
            return cached
        if self.config.offline:
            return {"results": []}
        return self.cache.set("http", url, self._request(url))

    @staticmethod
    def _parse_author(
        row: dict[str, Any], preferred_country_codes: list[str] | None = None
    ) -> OpenAlexAuthor:
        institution = OpenAlexClient._preferred_institution(row, preferred_country_codes or [])
        concepts = [
            concept.get("display_name", "")
            for concept in row.get("x_concepts", [])
            if concept.get("display_name")
        ]
        return OpenAlexAuthor(
            id=row.get("id", ""),
            display_name=row.get("display_name", ""),
            works_count=row.get("works_count") or 0,
            cited_by_count=row.get("cited_by_count") or 0,
            institution=institution.get("display_name"),
            country_code=institution.get("country_code"),
            institution_country=institution.get("country"),
            concepts=concepts,
            raw=row,
        )

    @staticmethod
    def _preferred_institution(
        row: dict[str, Any], preferred_country_codes: list[str]
    ) -> dict[str, Any]:
        for affiliation in row.get("affiliations", []):
            institution = affiliation.get("institution") or {}
            if (
                institution.get("type") == "education"
                and institution.get("country_code") in preferred_country_codes
            ):
                return institution
        for institution in row.get("last_known_institutions") or []:
            if (
                institution.get("type") == "education"
                and institution.get("country_code") in preferred_country_codes
            ):
                return institution
        for affiliation in row.get("affiliations", []):
            institution = affiliation.get("institution") or {}
            if institution.get("type") == "education":
                return institution
        last_known = row.get("last_known_institution") or {}
        if last_known:
            return last_known
        institutions = row.get("last_known_institutions") or []
        return institutions[0] if institutions else {}


def _authorship_has_target_education(authorship: dict[str, Any], country_codes: list[str]) -> bool:
    for institution in authorship.get("institutions") or []:
        if (
            institution.get("country_code") in country_codes
            and institution.get("type") == "education"
        ):
            return True
    return False
