import asyncio
import os
from cartesia import AsyncCartesia

async def main():
    # 1. Get Context Variables (building information)
    building_context = {
        "building_address": "401 North Wabash Avenue, Chicago, IL",
        "building_number": "+1-555-0199",
        "building_name": "Trump International Hotel & Tower"
    }
    print(f"Deploying agent with context: {building_context}")
    
    # 2. Initialize Cartesia Client
    # Make sure CARTESIA_API_KEY is set in your deployment environment
    api_key = os.getenv("CARTESIA_API_KEY")
    if not api_key:
        raise ValueError("CARTESIA_API_KEY environment variable is not set")
    
    client = AsyncCartesia(api_key=api_key)
    
    # 3. Create system prompt with building context
    system_prompt = f"""You are a helpful voice assistant for a building information system.
    
Building Information:
- Name: {building_context['building_name']}
- Address: {building_context['building_address']}
- Contact Number: {building_context['building_number']}

When users ask about the building address or number, provide them with the building name and relevant information from the context above."""
    
    # 4. Configure the voice agent
    # Replace with your actual agent_id from Cartesia Playground
    agent_config = {
        "agent_id": "your_agent_id_from_playground",
        "system_prompt": system_prompt,
        "context_variables": building_context
    }
    
    print(f"Agent configured with ID: {agent_config['agent_id']}")
    print("Agent is ready to receive calls...")
    
    # 5. Keep the service running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nShutting down agent...")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
