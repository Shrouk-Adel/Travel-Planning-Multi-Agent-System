import json
import logging
from typing import Any

from langchain_core.messages import AIMessage

from Travel_State import TravelState
from MCP_Severs import aviation_mcp_call
from .airport_data import find_main_airport

logger = logging.getLogger(__name__)

MAX_FLIGHTS = 5  # how many flight options to carry forward in state


def _parse_mcp_result(result: Any) -> dict:
    """MCP results are content blocks: [{"type": "text", "text": "...", "id": "..."}].
    Extract and parse the JSON payload. Returns {"ok": False} shape on failure
    so callers can branch on .get("ok")."""
    if not result:
        return {"ok": False, "error": "empty MCP result"}

    text_parts = [
        block.get("text", "")
        for block in result
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    raw_text = "".join(text_parts).strip()

    if not raw_text:
        return {"ok": False, "error": "empty text payload"}

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        logger.warning("Could not parse MCP result as JSON: %r", raw_text[:200])
        return {"ok": False, "error": "unparseable payload"}


def _condense_flights(flights: list, max_flights: int = MAX_FLIGHTS) -> list:
    """
    Raw AviationStack flight objects carry a lot of null/irrelevant fields
    (terminal, gate, baggage, runway timestamps, icao24, empty codeshared, etc).
    Keep only what downstream agents (Budget/Itinerary) actually need, and
    cap how many we carry forward in state.
    """
    condensed = []
    for f in flights[:max_flights]:
        dep = f.get("departure", {}) or {}
        arr = f.get("arrival", {}) or {}
        airline = f.get("airline", {}) or {}
        flight = f.get("flight", {}) or {}

        condensed.append({
            "airline": airline.get("name"),
            "flight_number": flight.get("iata"),
            "status": f.get("flight_status"),
            "departure_airport": dep.get("iata"),
            "departure_time": dep.get("scheduled"),
            "departure_delay_min": dep.get("delay"),
            "arrival_airport": arr.get("iata"),
            "arrival_time": arr.get("scheduled"),
        })
    return condensed


async def flight_agent(state: TravelState):
    logger.info("Start Flight Agent")

    constraints = state.get("trip_constraints", {})
    origin = constraints.get("origin")
    destination = constraints.get("destination")

    if not origin or not destination:
        return {
            "flight_results": {},
            "messages": [AIMessage(content="Origin or destination is missing.")],
        }

    try:
        departure = find_main_airport(origin)
        arrival = find_main_airport(destination)

        logger.info("main airport in departure: %s", departure)
        logger.info("main airport in arrival: %s", arrival)

        if not departure or not arrival:
            return {
                "flight_results": {},
                "messages": [
                    AIMessage(content="Could not find airports for the requested route.")
                ],
            }

        params = {
            "dep_iata": departure["iata_code"],
            "arr_iata": arrival["iata_code"],
            "limit": 5,
        }

        logger.info("AviationStack flights request params: %s", params)
        raw_result = await aviation_mcp_call("get_flights", params)
        logger.info("AviationStack flights response: %s", raw_result)

        parsed = _parse_mcp_result(raw_result)

        if not parsed.get("ok", True) and "error" in parsed:
            # Explicit API/tool error (bad key, plan restriction, etc.)
            logger.warning("AviationStack error: %s", parsed.get("error"))
            return {
                "flight_results": {"data_source": "error", "error": parsed.get("error")},
                "messages": [AIMessage(content="Flight lookup failed — please try again later.")],
            }

        flights = parsed.get("flights", [])
        condensed_flights = _condense_flights(flights)

        logger.info(
            "flights condensed: %d -> %d entries", len(flights), len(condensed_flights)
        )

        data_source = "live_schedule" if condensed_flights else "none"

        message = (
            "Flight schedule found for this route."
            if condensed_flights
            else "No flights found for this route today — a connecting itinerary is likely required."
        )

        return {
            "flight_results": {
                # keep only the essentials from find_main_airport too,
                # in case it returns a bulkier record than iata/name/city
                "departure_airport": {
                    "iata_code": departure.get("iata_code"),
                    "name": departure.get("name"),
                    "city": departure.get("city"),
                },
                "arrival_airport": {
                    "iata_code": arrival.get("iata_code"),
                    "name": arrival.get("name"),
                    "city": arrival.get("city"),
                },
                "flights": condensed_flights,
                "data_source": data_source,
            },
            "messages": [AIMessage(content=message)],
        }

    except Exception:
        logger.error("Flight Agent failed", exc_info=True)
        return {
            "flight_results": {},
            "messages": [AIMessage(content="Flight search failed.")],
        }