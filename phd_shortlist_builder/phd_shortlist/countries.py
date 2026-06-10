from __future__ import annotations

COUNTRY_TO_ISO2 = {
    "australia": "AU",
    "canada": "CA",
    "germany": "DE",
    "ireland": "IE",
    "netherlands": "NL",
    "new zealand": "NZ",
    "singapore": "SG",
    "sweden": "SE",
    "switzerland": "CH",
    "united kingdom": "GB",
    "uk": "GB",
    "england": "GB",
    "scotland": "GB",
    "united states": "US",
    "usa": "US",
    "us": "US",
}

ISO2_TO_COUNTRY = {
    "AU": "Australia",
    "CA": "Canada",
    "DE": "Germany",
    "GB": "United Kingdom",
    "IE": "Ireland",
    "NL": "Netherlands",
    "NZ": "New Zealand",
    "SG": "Singapore",
    "SE": "Sweden",
    "CH": "Switzerland",
    "US": "United States",
}


def normalize_country_to_iso2(country: str) -> str:
    key = country.strip().lower()
    if len(country.strip()) == 2:
        return country.strip().upper()
    if key not in COUNTRY_TO_ISO2:
        raise ValueError(f"Unsupported or unknown target country: {country}")
    return COUNTRY_TO_ISO2[key]


def country_name(iso2: str | None) -> str:
    if not iso2:
        return "Unknown"
    return ISO2_TO_COUNTRY.get(iso2.upper(), iso2.upper())
