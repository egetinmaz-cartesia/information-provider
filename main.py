import asyncio
from dotenv import load_dotenv
from line import VoiceAgentSystem

# Load environment variables
load_dotenv()

async def main():
    building_context = {
        "building_address": "401 North Wabash Avenue, Chicago, IL",
        "building_number": "+1-555-0199",
        "building_name": "Trump International Hotel & Tower"
    }

    print("--- Starting Agent ---")
    print(f"Injecting Context: {building_context}")

    system = VoiceAgentSystem(
        agent_id="agent_7CcsA878NH514PoBs6rF5z"
    )

    try:
        await system.start(
            context_variables=building_context
        )

        # Keep process alive
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        print("\nStopping agent...")
        await system.stop()

if __name__ == "__main__":
    asyncio.run(main())
