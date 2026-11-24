import os
import certifi
from langchain_groq import ChatGroq
from typing import Annotated,TypedDict
import operator
import uuid
from langgraph.graph import StateGraph,START,END
from langchain_core.messages import AIMessage, AIMessage, AnyMessage, HumanMessage, SystemMessage, SystemMessage
from langgraph.checkpoint.postgres import PostgresSaver
from dotenv import load_dotenv
import psycopg

from tools.flight_tool import search_flights
from tools.tavily_tool import search
load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in the environment variables.")



def get_database_url():
    DATABASE_URL = os.getenv("DATABASE_URL")

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is missing and not set in the environment variables.")

    if "sslmode=" not in DATABASE_URL:
        if "?" in DATABASE_URL:
            DATABASE_URL += "&sslmode=require"
        else:
            DATABASE_URL += "?sslmode=require"

    return DATABASE_URL


# Create LLM
llm = ChatGroq(api_key=GROQ_API_KEY,model="qwen/qwen3.8-27b",temperature=0,
    max_tokens=700)

#State

class TravelState(TypedDict):
    messages:Annotated[list[AnyMessage], operator.add]
    user_query:str
    flight_results:str
    hotel_results:str
    itenary_results:str
    llm_calls:int


# Flight Agent
def flight_agent(state:TravelState):
    user_query = state["user_query"]
    flight_results = search_flights(user_query)
    return {
        "flight_results": flight_results,
        "messages": [
            AIMessage(content='Flight results fetched successfully.'),
        ],
        # "llm_calls": state.get("llm_calls", 0) + 1
        }

# Hotel Agent
def hotel_agent(state:TravelState):
    user_query = state["user_query"]
    hotel_results = search(user_query)
    return {
        "hotel_results": hotel_results,
        "messages": [
            AIMessage(content='Hotel results fetched successfully.'),
        ],
        # "llm_calls": state.get("llm_calls", 0) + 1
        }

#Itenary Agent
def itenary_agent(state:TravelState):
    prompt = f"""
    Create a complete travel itenary.
    Based on the user's query and the flight and hotel results.

    user_query: {state['user_query']}
    flight_results: {state['flight_results']}
    hotel_results: {state['hotel_results']}

    Make the itinerary practical, budget-aware, and easy to follow.

    """

    response = llm.invoke([
        SystemMessage(content="You are an expert travel planner."),
        HumanMessage(content=prompt)
    ])

    return {
        "itenary_results": response.content,
        "messages": [
            response
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }

# Final Agent

def final_agent(state:TravelState):
    prompt = f"""
    Create a final travel plan.
    Based on the user's query and the flight, hotel, and itinerary results.

    User Request: {state['user_query']}
    Flights : {state['flight_results']}
    Hotels : {state['hotel_results']}
    Itinerary : {state['itenary_results']}

    Make the final travel plan practical, budget-aware, and easy to follow.
    Format the final answer beautifully using these sections:

    1. Trip Summary
    2. Flight Information
    3. Hotel Suggestions
    4. Day-by-Day Itinerary
    5. Estimated Budget
    6. Final Recommendations

    Important:
    - Be clear and practical.
    - Mention that live flight API may not provide ticket prices if pricing is unavailable.
    - Keep the response useful for real travel planning.

    """

    response = llm.invoke([
        SystemMessage(content="You are an expert travel planner."),
        HumanMessage(content=prompt)
    ])

    return {
        "messages": [
            response
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# Build Graph

graph = StateGraph(TravelState)

graph.add_node('flight_agent', flight_agent)
graph.add_node('hotel_agent', hotel_agent)
graph.add_node('itenary_agent', itenary_agent)
graph.add_node('final_agent', final_agent)

# graph.add_edge(START, 'flight_agent')
# graph.add_edge('flight_agent', 'hotel_agent')
# graph.add_edge('hotel_agent', 'itenary_agent')
# graph.add_edge('itenary_agent', 'final_agent')
graph.add_edge(START, "flight_agent")
graph.add_edge(START, "hotel_agent")

graph.add_edge(
    ["flight_agent", "hotel_agent"],
    "itenary_agent"
)

graph.add_edge("itenary_agent", "final_agent")
graph.add_edge('final_agent', END)

# PostGre SQl Checkpointer
Database_URL = get_database_url()

_conn = psycopg.connect(Database_URL, autocommit=True,row_factory=psycopg.rows.dict_row)

checkpointer = PostgresSaver(_conn)
checkpointer.setup()

travel_graph = graph.compile(checkpointer=checkpointer)

# Function for Fast API

def run_travel_agent(user_input:str,thread_id:str | None=None):
    if not thread_id:
        thread_id = f" user_{uuid.uuid4().hex}"

    config = {
        "configurable":{
            'thread_id':thread_id
        }
    }

    result = travel_graph.invoke(
        {
            "messages":[
                HumanMessage(content=user_input)
            ],
            "user_query": user_input,
            "flight_results": "",
            "hotel_results": "",
            "itenary_results": "",
            "llm_calls": 0
        },
        config = config
    )

    final_result = result["messages"][-1].content

    return {
        "thread_id": thread_id,
        "answer": final_result,
        "flight_results": result.get("flight_results", ""),
        "hotel_results": result.get("hotel_results", ""),
        "itinerary": result.get("itenary_results", ""),
        "llm_calls": result.get("llm_calls", 0),
    }


