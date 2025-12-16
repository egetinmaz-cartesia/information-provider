from fastapi import FastAPI
from line import Agent, tool

app = FastAPI()

# Your building database
BUILDINGS = {
    "401 north wabash": "Trump International Hotel & Tower",
    "401 north wabash avenue": "Trump International Hotel & Tower",
    "+1-555-0199": "Trump International Hotel & Tower",
    "555-0199": "Trump International Hotel & Tower"
}

@tool
def lookup_building(address_or_number: str) -> str:
    """
    Look up a building name by address or phone number.
    
    Args:
        address_or_number: The building address or phone number to look up
        
    Returns:
        The building name if found, otherwise an error message
    """
    # Normalize the query
    query = address_or_number.lower().strip()
    
    # Search through buildings
    for key, name in BUILDINGS.items():
        if key in query or query in key:
            return f"That building is {name}."
    
    return "I couldn't find that building. Please provide the full address or phone number."

# Create the agent with your custom tool
agent = Agent(
    prompt="""You are a helpful building information assistant. 
    
When someone asks about a building and gives you an address or phone number, use the lookup_building tool to find the building name and tell them the answer in a friendly way.""",
    tools=[lookup_building],
)

# This makes the agent available to Cartesia
app.include_router(agent.router)
