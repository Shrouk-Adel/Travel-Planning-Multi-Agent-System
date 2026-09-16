import csv
import io
from pathlib import Path

import httpx
import pycountry


AIRPORTS_CSV_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
LOCAL_CACHE = Path("data/airports.csv")

_AIRPORTS_BY_IATA: dict[str, dict] = {}
_AIRPORTS_BY_CITY: dict[str, list[dict]] = {}
_AIRPORTS_BY_COUNTRY: dict[str, list[dict]] = {}


def _load_rows() -> list[dict]:

    if LOCAL_CACHE.exists():

        text = LOCAL_CACHE.read_text(
            encoding="utf-8"
        )

    else:

        resp = httpx.get(
            AIRPORTS_CSV_URL,
            timeout=30
        )

        resp.raise_for_status()

        text = resp.text

        LOCAL_CACHE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        LOCAL_CACHE.write_text(
            text,
            encoding="utf-8"
        )

    return list(
        csv.DictReader(
            io.StringIO(text)
        )
    )


def load_airport_index() -> None:
    """
    Load airport data once at application startup.
    """

    # Clear previous data in case this function
    # is called more than once.
    _AIRPORTS_BY_IATA.clear()
    _AIRPORTS_BY_CITY.clear()
    _AIRPORTS_BY_COUNTRY.clear()

    rows = _load_rows()

    for row in rows:

        iata = (
            row.get("iata_code") or ""
        ).strip().upper()

        airport_type = (
            row.get("type") or ""
        ).strip()

        if not iata:
            continue

        if airport_type not in (
            "large_airport",
            "medium_airport"
        ):
            continue

        entry = {
            "airport_name": (
                row.get("name") or ""
            ).strip(),

            "iata_code": iata,

            "country_name": (
                row.get("iso_country") or ""
            ).strip().upper(),

            "municipality": (
                row.get("municipality") or ""
            ).strip(),

            "type": airport_type
        }

        # -------------------------
        # IATA index
        # -------------------------
        _AIRPORTS_BY_IATA[iata] = entry

        # -------------------------
        # City index
        # -------------------------
        city = entry["municipality"]

        if city:

            city_key = city.lower()

            _AIRPORTS_BY_CITY.setdefault(
                city_key,
                []
            ).append(entry)

        # -------------------------
        # Country index
        # -------------------------
        country = entry["country_name"]

        if country:

            _AIRPORTS_BY_COUNTRY.setdefault(
                country,
                []
            ).append(entry)

    print(
        f"Loaded {len(_AIRPORTS_BY_IATA)} airports"
    )


def country_to_iso2(
    country_name: str
) -> str | None:

    try:

        match = pycountry.countries.search_fuzzy(
            country_name
        )

        return (
            match[0].alpha_2
            if match
            else None
        )

    except LookupError:

        return None


def find_main_airport(
    place: str
) -> dict | None:

    if not place:
        return None

    place = place.strip()

    if not place:
        return None

    # --------------------------------
    # 1. Direct IATA lookup
    # --------------------------------

    iata = place.upper()

    if iata in _AIRPORTS_BY_IATA:

        return _AIRPORTS_BY_IATA[iata]

    # --------------------------------
    # 2. Country lookup
    # --------------------------------

    iso2 = country_to_iso2(place)

    if iso2:

        candidates = _AIRPORTS_BY_COUNTRY.get(
            iso2.upper(),
            []
        )

        if candidates:

            large_airports = [
                airport
                for airport in candidates
                if airport["type"] == "large_airport"
            ]

            return (
                large_airports[0]
                if large_airports
                else candidates[0]
            )

    # --------------------------------
    # 3. Exact city lookup
    # --------------------------------

    city_key = place.lower()

    candidates = _AIRPORTS_BY_CITY.get(
        city_key,
        []
    )

    if candidates:

        large_airports = [
            airport
            for airport in candidates
            if airport["type"] == "large_airport"
        ]

        return (
            large_airports[0]
            if large_airports
            else candidates[0]
        )

    # --------------------------------
    # 4. Partial city lookup
    # --------------------------------

    for city, airports in _AIRPORTS_BY_CITY.items():

        if (
            city_key in city
            or city in city_key
        ):

            large_airports = [
                airport
                for airport in airports
                if airport["type"] == "large_airport"
            ]

            return (
                large_airports[0]
                if large_airports
                else airports[0]
            )

    return None

