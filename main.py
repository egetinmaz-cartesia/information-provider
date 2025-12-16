from cartesia_line import Agent

# Building database - simple lookup
buildings = {
    "401 North Wabash Avenue, Chicago, IL": "Trump International Hotel & Tower",
    "+1-555-0199": "Trump International Hotel & Tower",
    "401 north wabash": "Trump International Hotel & Tower",
}

def get_building_name(query: str) -> str:
    """Look up building name by address or number"""
    query_lower = query.lower()
    
    # Check each building key
    for key, name in buildings.items():
        if key.lower() in query_lower:
            return name
    
    return "Building not found. Please provide a valid address or phone number."

# Create the agent - this is what Cartesia will run
agent = Agent(
    system_prompt="""You are a building information assistant. 
    
When someone gives you a building address or phone number, use the get_building_name function to look it up and tell them the building name in a friendly way.""",
    tools=[get_building_name]
)
