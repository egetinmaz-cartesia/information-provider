import os
from chat_node import ChatNode
from google import genai
from loguru import logger
from line import Bridge, CallRequest, VoiceAgentApp, VoiceAgentSystem
from line.events import UserStartedSpeaking, UserStoppedSpeaking, UserTranscriptionReceived

# System prompt for the agent
SYSTEM_PROMPT = """You are a helpful building information assistant.

When someone asks about a building and provides an address or phone number, use the lookup_building function to find the building name and tell them the answer in a friendly, conversational way.

Be natural and friendly in your responses."""

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
else:
    gemini_client = None

# ============ ADD YOUR BUILDING LOOKUP FUNCTION HERE ============
BUILDINGS = {
    "401 north wabash": "Trump International Hotel & Tower",
    "401 north wabash avenue": "Trump International Hotel & Tower",
    "401 north wabash avenue, chicago, il": "Trump International Hotel & Tower",
    "+1-555-0199": "Trump International Hotel & Tower",
    "555-0199": "Trump International Hotel & Tower",
}

def lookup_building(address_or_number: str) -> str:
    """
    Look up a building name by address or phone number.
    
    Args:
        address_or_number: The building address or phone number to look up
        
    Returns:
        The building name if found, otherwise an error message
    """
    query = address_or_number.lower().strip()
    
    # Search through buildings
    for key, name in BUILDINGS.items():
        if key in query or query in key:
            return f"The building is {name}."
    
    return "I couldn't find that building. Please provide the full address or phone number."
# ================================================================

async def handle_new_call(system: VoiceAgentSystem, call_request: CallRequest):
    logger.info(
        f"Starting new call for {call_request.call_id}. "
        f"Call request: { {k: v for k, v in call_request.__dict__.items() if k != 'agent'} }, "
        f"agent.system_prompt: {call_request.agent.system_prompt[:100] if getattr(call_request.agent, 'system_prompt', None) else None}, "
        f"agent.introduction: {call_request.agent.introduction[:100] if getattr(call_request.agent, 'introduction', None) else None}. "
    )
    
    # Main conversation node with building lookup tool
    conversation_node = ChatNode(
        system_prompt=call_request.agent.system_prompt or SYSTEM_PROMPT,
        gemini_client=gemini_client,
        tools=[lookup_building],  # ADD YOUR TOOL HERE
    )
    
    conversation_bridge = Bridge(conversation_node)
    system.with_speaking_node(conversation_node, bridge=conversation_bridge)
    conversation_bridge.on(UserTranscriptionReceived).map(conversation_node.add_event)
    
    (
        conversation_bridge.on(UserStoppedSpeaking)
        .interrupt_on(UserStartedSpeaking, handler=conversation_node.on_interrupt_generate)
        .stream(conversation_node.generate)
        .broadcast()
    )
    
    await system.start()
    
    # The agent will wait for the user to speak first if no introduction is provided.
    introduction = call_request.agent.introduction or "Hello! I'm your building information assistant. How can I help you today?"
    await system.send_initial_message(introduction)
    
    await system.wait_for_shutdown()

app = VoiceAgentApp(handle_new_call)

if __name__ == "__main__":
    app.run()
