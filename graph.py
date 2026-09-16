from graph_nodes import *
from Travel_State import AGENT_ORDER, TravelState, selected_agents_in_order
from langgraph.graph import StateGraph, START, END

from dotenv import load_dotenv

load_dotenv()

# =========================
# Build Graph
# =========================
graph = StateGraph(TravelState)

graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("weather_agent", Weather_Agent)
graph.add_node("budget_agent", Budget_Agent)
graph.add_node("itinerary_agent", Itinerary_Agent)
graph.add_node("human_approval", human_approval_agent)
graph.add_node("final_agent", final_agent)


ROUTE_MAP = {
    "flight_agent": "flight_agent",
    "hotel_agent": "hotel_agent",
    "weather_agent": "weather_agent",
    "budget_agent": "budget_agent",
    "itinerary_agent": "itinerary_agent",
}


def route_from_start(state: TravelState) -> str:
    selected = selected_agents_in_order(state)
    return selected[0] if selected else "itinerary_agent"


def route_after_agent(current_agent: str):
    def route(state: TravelState) -> str:
        selected = selected_agents_in_order(state)
        current_index = AGENT_ORDER.index(current_agent)

        for next_agent in AGENT_ORDER[current_index + 1:]:
            if next_agent in selected:
                return next_agent

        return "itinerary_agent"

    return route


graph.add_conditional_edges(START, route_from_start, ROUTE_MAP)

graph.add_conditional_edges(
    "flight_agent", route_after_agent("flight_agent"), ROUTE_MAP
)
graph.add_conditional_edges(
    "hotel_agent", route_after_agent("hotel_agent"), ROUTE_MAP
)
graph.add_conditional_edges(
    "weather_agent", route_after_agent("weather_agent"), ROUTE_MAP
)
graph.add_conditional_edges(
    "budget_agent", route_after_agent("budget_agent"), ROUTE_MAP
)

graph.add_edge("itinerary_agent", "human_approval")
graph.add_edge("human_approval", "final_agent")
graph.add_edge("final_agent", END)


def compile_travel_graph(checkpointer):
    return graph.compile(checkpointer=checkpointer)