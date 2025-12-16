import asyncio
import os
from dotenv import load_dotenv

# Import the Line framework components
# NOTE: Adjust these imports based on your specific Line version/location
from line import VoiceAgentSystem, ConversationHarness 

# 1. Load environment variables from .env file
load_dotenv()

async def main():
    # 2. Define the dynamic data you want to inject
    # These keys MUST match the {{placeholders}} in your Cartesia Playground Prompt
    building_context = {
        "building_address": "401 North Wabash Avenue, Chicago, IL",
        "building_number": "+1-555-0199",
        "building_name": "Trump International Hotel & Tower"
    }

    print("--- Starting Agent ---")
    print(f"Injecting Context: {building_context}")

    # 3. Initialize the System (Assuming standard Line setup)
    # You might need to pass a specific agent_id or deployment_id here
    system = VoiceAgentSystem(
        agent_id="your_agent_id_from_playground" 
    )

    # 4. Initialize the Harness (Handling the connection/audio)
    harness = ConversationHarness(system)

    try:
        # 5. Start the call with the Context Variables
        # This is the magic step that overwrites the Playground defaults
        await harness.start(
            context_variables=building_context
        )
        
        # Keep the process alive or wait for user termination
        # (The harness usually handles the loop, but we ensure it runs)
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        print("\nStopping agent...")
        await harness.stop()

if __name__ == "__main__":
    asyncio.run(main())
