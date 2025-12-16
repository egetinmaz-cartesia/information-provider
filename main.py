from fastapi import FastAPI
from line import VoiceAgent

app = FastAPI()

# Building database - simple lookup
buildings = {
    "401 North Wabash Avenue, Chicago, IL": "Trump International Hotel & Tower",
    "+1-555-0199": "Trump International Hotel & Tower",
    "401 north wabash": "Trump International Hotel & Tower",
}

def get_building_name(address_or_number: str) -> str:
    """Look up building name by address or phone number"""
    query = address_or_number.lower()
    
    # Check each building key
    for key, name in buildings.items():
        if key.lower() in query:
            return f"The building is {name}"
    
    return "I couldn't find that building. Can you provide the full address or phone number?"

# Create the voice agent
agent = VoiceAgent(
    system_prompt="""You are a building information assistant. 
    
When someone gives you a building address or phone number, call the get_building_name function to look it up and tell them the building name.""",
    tools=[get_building_name]
)

# Mount the agent to FastAPI
app.include_router(agent.router)
