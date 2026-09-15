from Travel_State import TravelState
from MCP_Severs import *
from prompts import FLIGHT_AGENT_PROMPT
from llm import OpenAIConfig
from langchain_core.messages import AIMessage
from config import settings

openai_config = OpenAIConfig()

from pydantic import BaseModel, Field
from typing import List, Optional, Any

import asyncio
import json
import logging

logger = logging.getLogger(__name__)

# Set to True once you've confirmed (as we have) that your AviationStack
# plan rejects `search`/`dep_iata`/`arr_iata` filtering with
# function_access_restricted. Skips straight to the LLM-based fallbacks
# instead of making two calls per lookup that are guaranteed to fail.
# Flip back to False if you upgrade the plan.
AVIATION_FILTERED_ENDPOINTS_RESTRICTED = getattr(
    settings, "AVIATION_FILTERED_ENDPOINTS_RESTRICTED", True
)

# In-memory cache: city/name (lowercased) -> resolved airport dict.
# Avoids repeating two guaranteed-to-fail AviationStack calls (search,
# then a paginated pull) plus a slow LLM call for the same city on every
# request. Cleared on process restart; fine since this only caches
# airport metadata, which doesn't change trip-to-trip.
_AIRPORT_CACHE: dict[str, dict] = {}

# In-memory cache: (dep_iata, arr_iata) -> list of airline dicts, for the
# LLM route-airline guess. Same rationale as _AIRPORT_CACHE.
_ROUTE_AIRLINES_CACHE: dict[tuple[str, str], list[dict]] = {}


class Airport(BaseModel):
    name: str = Field(description="Full airport name")
    iata_code: str = Field(description="3-letter IATA airport code")
    city: str = Field(description="City where the airport is located")
    country: Optional[str] = Field(
        default=None,
        description="Country where the airport is located"
    )


class Airline(BaseModel):
    name: str = Field(description="Airline name")
    iata_code: Optional[str] = Field(
        default=None,
        description="2-letter IATA airline code"
    )


class FlightAgentResponse(BaseModel):
    departure_airport: Optional[Airport] = Field(
        default=None,
        description="Most likely departure airport"
    )

    arrival_airport: Optional[Airport] = Field(
        default=None,
        description="Most likely arrival airport"
    )

    airlines: List[Airline] = Field(
        default_factory=list,
        description="Airlines that typically serve this route"
    )

    typical_flight_duration: Optional[str] = Field(
        default=None,
        description="Typical flight duration, e.g. '3h 45m'"
    )

    estimated_airfare_range: Optional[str] = Field(
        default=None,
        description="Estimated airfare range, including currency, e.g. 'USD 250–450'"
    )

    peak_season_warning: Optional[str] = Field(
        default=None,
        description="Warning about higher prices during peak travel periods"
    )

    booking_advice: List[str] = Field(
        default_factory=list,
        description="Practical booking recommendations"
    )


def _parse_mcp_json_list(mcp_result: Any) -> list[dict]:
    """The aviationstack-mcp tools return LangChain content blocks like
    [{'type': 'text', 'text': '[{...json array...}]', 'id': ...}] on success,
    or [{'type': 'text', 'text': '{"ok": false, "error": "..."}', 'id': ...}]
    when the underlying AviationStack API call fails (e.g. a plan/subscription
    restriction on that endpoint). This unwraps the success case into a list
    of dicts, and logs (rather than silently swallowing) the error case.
    """
    if not mcp_result or not isinstance(mcp_result, list):
        return []

    combined: list[dict] = []
    for block in mcp_result:
        text = block.get("text") if isinstance(block, dict) else None
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            continue

        if isinstance(parsed, list):
            combined.extend(parsed)
        elif isinstance(parsed, dict) and parsed.get("ok") is False:
            logger.warning(
                "AviationStack API call failed (%s): %s",
                parsed.get("context", "unknown context"),
                parsed.get("error", "no error message"),
            )
    return combined


def _matches_place(entry: dict, place: str) -> bool:
    if not place:
        return False
    place_lower = place.strip().lower()
    if not place_lower:
        return False

    haystacks = [
        entry.get("airport_name", ""),
        entry.get("city_iata_code", "") or "",
        entry.get("country_name", "") or "",
    ]
    return any(place_lower in str(h).lower() for h in haystacks if h)


class _AirportIataGuess(BaseModel):
    iata_code: str = Field(
        description="The 3-letter IATA code of the primary international "
        "airport serving this city (e.g. 'DXB' for Dubai). Empty string if unknown."
    )
    airport_name: str = Field(
        default="",
        description="Full name of that airport, if known."
    )


async def _resolve_iata_via_llm(city_or_name: str) -> dict | None:
    """Last-resort fallback: ask the LLM directly for the primary airport
    IATA code for a city — or, if given a country, that country's busiest/
    primary international hub airport. Used when the aviationstack search
    filter is plan-restricted and paginating the full unfiltered airport
    list would be too slow/unreliable to reach an alphabetically distant
    entry.
    """
    if not city_or_name:
        return None

    try:
        guess = await openai_config.generate_response(
            prompt=(
                f"What is the IATA code of the main international airport "
                f"for '{city_or_name}'?\n\n"
                f"- If this is a specific city, give that city's primary "
                f"international airport.\n"
                f"- If this is a country (not a specific city), give the "
                f"busiest/primary international hub airport in that "
                f"country instead of refusing — e.g. for 'Japan' answer "
                f"with Tokyo Haneda or Narita, for 'France' answer with "
                f"Paris Charles de Gaulle.\n"
                f"- Always return a real 3-letter IATA code; never answer "
                f"'N/A' or explain why one can't be chosen.\n\n"
                f"Respond with the code and airport name only."
            ),
            pydantic_schema=_AirportIataGuess,
        )
    except Exception:
        logger.warning("LLM-based IATA resolution failed for %r", city_or_name, exc_info=True)
        return None

    iata_code = (guess or {}).get("iata_code", "").strip().upper()
    if not iata_code:
        return None

    return {
        "airport_name": (guess or {}).get("airport_name", ""),
        "iata_code": iata_code,
        "city_iata_code": "",
        "country_name": "",
    }


class _RouteAirlinesGuess(BaseModel):
    airlines: List[Airline] = Field(
        default_factory=list,
        description="Airlines that commonly operate flights on this specific route."
    )


async def _guess_route_airlines(
    dep_iata: str, arr_iata: str, dep_airport_name: str, arr_airport_name: str
) -> list[dict]:
    """Last-resort fallback for route-specific airline data: ask the LLM
    which airlines typically serve this specific route. Used when
    list_routes is plan-restricted, so the generic global airline list
    would otherwise be the only fallback (and is unrelated to the route)."""
    if not dep_airport_name or not arr_airport_name:
        return []

    cache_key = (dep_iata, arr_iata)
    if cache_key in _ROUTE_AIRLINES_CACHE:
        logger.info("Route-airline cache hit for %s -> %s", dep_iata, arr_iata)
        return _ROUTE_AIRLINES_CACHE[cache_key]

    try:
        guess = await openai_config.generate_response(
            prompt=(
                f"List airlines that commonly operate flights between "
                f"{dep_airport_name} and {arr_airport_name}. Include only "
                f"airlines you are confident actually serve this route."
            ),
            pydantic_schema=_RouteAirlinesGuess,
        )
    except Exception:
        logger.warning(
            "LLM-based route airline guess failed for %s -> %s",
            dep_airport_name, arr_airport_name, exc_info=True,
        )
        return []

    airlines = (guess or {}).get("airlines", [])
    airlines = airlines if isinstance(airlines, list) else []
    if airlines and dep_iata and arr_iata:
        _ROUTE_AIRLINES_CACHE[cache_key] = airlines
    return airlines


async def _find_airport(city_or_name: str) -> dict | None:
    """Find the best-matching airport for a city/airport name.

    Tries the server-side `search` filter first. Some AviationStack plans
    restrict that parameter (returns an "ok": false / function_access_restricted
    error even though the base endpoint works). If so, falls back to a
    capped unfiltered pull + client-side match (catches cities near the
    front of the alphabetically-sorted dataset), and finally to an
    LLM-based IATA code guess (catches everything else, cheaply).
    """
    if not city_or_name:
        return None

    cache_key = city_or_name.strip().lower()
    if cache_key in _AIRPORT_CACHE:
        logger.info("Airport cache hit for %r", city_or_name)
        return _AIRPORT_CACHE[cache_key]

    if not AVIATION_FILTERED_ENDPOINTS_RESTRICTED:
        result = await aviation_mcp_call(
            "list_airports",
            {"search": city_or_name, "limit": 5},
        )
        matches = _parse_mcp_json_list(result)
        if matches:
            _AIRPORT_CACHE[cache_key] = matches[0]
            return matches[0]

        logger.info(
            "list_airports(search=%r) returned nothing; trying a capped "
            "unfiltered pull + client-side match.",
            city_or_name,
        )
        fallback_result = await aviation_mcp_call("list_airports", {"limit": 100})
        fallback_entries = _parse_mcp_json_list(fallback_result)
        fallback_matches = [e for e in fallback_entries if _matches_place(e, city_or_name)]
        if fallback_matches:
            _AIRPORT_CACHE[cache_key] = fallback_matches[0]
            return fallback_matches[0]

        logger.info(
            "No match for %r in the first 100 airports either "
            "(likely alphabetically distant); falling back to LLM IATA lookup.",
            city_or_name,
        )
    else:
        logger.info(
            "AVIATION_FILTERED_ENDPOINTS_RESTRICTED=True; skipping "
            "list_airports search/pagination for %r and going straight "
            "to LLM IATA lookup.",
            city_or_name,
        )

    resolved = await _resolve_iata_via_llm(city_or_name)
    if resolved:
        _AIRPORT_CACHE[cache_key] = resolved
    return resolved


async def flight_agent(state: TravelState) -> dict:

    try:
        logger.info("start flight agent")
        query = state.get("user_query", "")
        trip_constraints = state.get("trip_constraints", {}) or {}
        origin = trip_constraints.get("origin", "")
        destination = trip_constraints.get("destination", "")

        # Step 1: resolve origin/destination to real IATA codes. Tries the
        # server's `search` filter first (list_airports(search=..., limit=...));
        # if that's plan-restricted or empty, _find_airport falls back to an
        # unfiltered pull + client-side match, then an LLM guess. Run both
        # lookups concurrently since they're independent — this alone cuts
        # a meaningful chunk of latency since each tier can involve a slow
        # LLM call.
        departure_airport, arrival_airport = await asyncio.gather(
            _find_airport(origin),
            _find_airport(destination),
        )

        dep_iata = (departure_airport or {}).get("iata_code", "")
        arr_iata = (arrival_airport or {}).get("iata_code", "")

        # Step 2: with real IATA codes, pull the routes/airlines that
        # actually serve this city pair via list_routes(dep_iata, arr_iata).
        # If restricted/empty, fall back to asking the LLM which airlines
        # typically serve this specific route — still route-relevant,
        # unlike the generic global airline list.
        routes: list[dict] = []
        if dep_iata and arr_iata and not AVIATION_FILTERED_ENDPOINTS_RESTRICTED:
            routes_result = await aviation_mcp_call(
                "list_routes",
                {"dep_iata": dep_iata, "arr_iata": arr_iata, "limit": 10},
            )
            routes = _parse_mcp_json_list(routes_result)

        route_specific_airlines: list[dict] = []
        if not routes and departure_airport and arrival_airport:
            route_specific_airlines = await _guess_route_airlines(
                dep_iata,
                arr_iata,
                departure_airport.get("airport_name", ""),
                arrival_airport.get("airport_name", ""),
            )

        # Final fallback: a generic global airline list, only used if we
        # have neither real route data nor an LLM route guess.
        general_airlines: list[dict] = []
        if not routes and not route_specific_airlines:
            airlines_result = await aviation_mcp_call(
                "list_airlines", {"limit": 15}
            )
            general_airlines = _parse_mcp_json_list(airlines_result)

        logger.info(f"DEPARTURE AIRPORT: {departure_airport}")
        logger.info(f"ARRIVAL AIRPORT: {arrival_airport}")
        logger.info(f"ROUTES: {routes}")
        if route_specific_airlines:
            logger.info(f"ROUTE-SPECIFIC AIRLINES (LLM guess): {route_specific_airlines}")
        if general_airlines:
            logger.info(f"GENERAL AIRLINES (fallback): {general_airlines}")

        airport_data = {
            "departure_airport": departure_airport,
            "arrival_airport": arrival_airport,
        }
        airline_data = routes or route_specific_airlines or general_airlines

        sys_prompt = FLIGHT_AGENT_PROMPT.format(
            query=query,
            airport_data=json.dumps(airport_data)[:3000],
            airline_data=json.dumps(airline_data)[:3000],
        )

        res = await openai_config.generate_response(
            prompt=sys_prompt,
            pydantic_schema=FlightAgentResponse,
        )

    except Exception as exp:
        logger.error("Flight Agent failed", exc_info=True)
        return {
            "flight_results": "",
            "messages": [
                AIMessage(content=f"Flight Agent failed with error: {exp}")
            ],
            "llm_calls": state.get("llm_calls", 0),
        }

    return {
        "flight_results": res,
        "messages": [AIMessage(content="Flight recommendations generated")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }