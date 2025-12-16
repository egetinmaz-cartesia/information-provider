import asyncio
import os
from cartesia_line import Agent, Context

# Define your building lookup function
def get_building_info(address: str = None, number: str = None) -> dict:
    """
    Look up building information by address or phone number.
    """
    # Building database (in production, this would be a real database)
    buildings = {
        "401 North Wabash Avenue, Chicago, IL": {
            "name": "Trump International Hotel & Tower",
            "address": "401 North Wabash Avenue, Chicago, IL",
            "number": "+1-555-0199"
        },
        "+1-555-0199": {
            "name": "Trump International Hotel & Tower",
            "address": "401 North Wabash Avenue, Chicago, IL",
            "number": "+1-555-0199"
        }
    }
    
    # Search by address or number
    search_key = address or number
    if search_key in buildings:
        return buildings[search_key]
    return {"error": "Building not found"}

# Create the agent
agent = Agent(
    name="Building Information Agent",
    system_prompt="""You are a helpful voice assistant for a building information system.
    
When users provide a building address or phone number, use the get_building_info function to look up the building name and details.

Be friendly and conversational. If you find the building, tell them the name and offer any additional information they might need.""",
    tools=[get_building_info],
    # Configure voice settings
    voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22",  # Default voice, change as needed
    language="en"
)

# This is the entry point for Cartesia deployment
async def main():
    """
    Main entry point for the Cartesia Line agent.
    """
    print("Building Information Agent is running...")
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
