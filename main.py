import os
from chat_node import ChatNode
from google import genai
from google.genai import types as gemini_types
from loguru import logger
from line import Bridge, CallRequest, VoiceAgentApp, VoiceAgentSystem
from line.events import AgentResponse, UserStartedSpeaking, UserStoppedSpeaking, UserTranscriptionReceived

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
else:
    gemini_client = None

# System prompt for the agent
SYSTEM_PROMPT = """You are a helpful building information assistant.

When someone asks about a building and provides an address or phone number, use the lookup_building function to find the building name and tell them the answer in a friendly, conversational way.

Be natural and friendly in your responses."""

# ============ BUILDING LOOKUP TOOL ============
BUILDINGS = {
    "401 north wabash": "Trump International Hotel & Tower",
    "401 north wabash avenue": "Trump International Hotel & Tower",
    "401 north wabash avenue, chicago, il": "Trump International Hotel & Tower",
    "+1-555-0199": "Trump International Hotel & Tower",
    "555-0199": "Trump International Hotel & Tower",
    "123 Sesame Street": "Eggy's House",
    "Sesame Street": "Eggy's House",
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
    
    for key, name in BUILDINGS.items():
        if key in query or query in key:
            return name
    
    return "Building not found. Please provide the full address or phone number."

# Define the tool in Gemini format
BuildingLookupTool = gemini_types.Tool(
    function_declarations=[
        gemini_types.FunctionDeclaration(
            name="lookup_building",
            description="Look up a building name by its address or phone number",
            parameters=gemini_types.Schema(
                type=gemini_types.Type.OBJECT,
                properties={
                    "address_or_number": gemini_types.Schema(
                        type=gemini_types.Type.STRING,
                        description="The building address or phone number to look up"
                    )
                },
                required=["address_or_number"]
            )
        )
    ]
)
# ==============================================


class BuildingChatNode(ChatNode):
    """Extended ChatNode that handles the building lookup tool"""
    
    async def process_context(self, context):
        """Override to handle our custom tool calls"""
        if not context.events:
            logger.info("No messages to process")
            return

        from line.utils.gemini_utils import convert_messages_to_gemini
        
        messages = convert_messages_to_gemini(context.events)
        user_message = context.get_latest_user_transcript_message()
        
        if user_message:
            logger.info(f'🧠 Processing user message: "{user_message}"')

        full_response = ""
        if not self.client:
            from chat_node import canned_gemini_response_stream
            stream = canned_gemini_response_stream()
        else:
            stream = await self.client.aio.models.generate_content_stream(
                model=self.model_id,
                contents=messages,
                config=self.generation_config,
            )

        async for msg in stream:
            if msg.text:
                full_response += msg.text
                yield AgentResponse(content=msg.text)

            # Handle function calls
            if msg.function_calls:
                for function_call in msg.function_calls:
                    if function_call.name == "lookup_building":
                        # Execute our building lookup
                        address = function_call.args.get("address_or_number", "")
                        result = lookup_building(address)
                        logger.info(f"🏢 Building lookup: {address} -> {result}")
                        
                        # Return the result to Gemini
                        yield AgentResponse(content=f"The building is {result}.")
                    
                    elif function_call.name == "end_call":
                        from line.tools.system_tools import EndCallArgs, end_call
                        goodbye_message = function_call.args.get("goodbye_message", "Goodbye!")
                        args = EndCallArgs(goodbye_message=goodbye_message)
                        logger.info(f"🤖 End call tool called: {args.goodbye_message}")
                        async for item in end_call(args):
                            yield item

        if full_response:
            logger.info(f'🤖 Agent response: "{full_response}" ({len(full_response)} chars)')


async def handle_new_call(system: VoiceAgentSystem, call_request: CallRequest):
    logger.info(
        f"Starting new call for {call_request.call_id}. "
        f"Call request: { {k: v for k, v in call_request.__dict__.items() if k != 'agent'} }, "
        f"agent.system_prompt: {call_request.agent.system_prompt[:100] if getattr(call_request.agent, 'system_prompt', None) else None}, "
        f"agent.introduction: {call_request.agent.introduction[:100] if getattr(call_request.agent, 'introduction', None) else None}. "
    )
    
    # Create our custom node with building lookup tool
    conversation_node = BuildingChatNode(
        system_prompt=SYSTEM_PROMPT,
        gemini_client=gemini_client,
    )
    
    # Add the building lookup tool to the generation config
    from line.tools.system_tools import EndCallTool
    conversation_node.generation_config.tools = [
        BuildingLookupTool,
        EndCallTool.to_gemini_tool()
    ]
    
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
    
    # Send introduction
    introduction = call_request.agent.introduction or "Hello! I'm your building information assistant. You can ask me about any building by providing its address or phone number."
    await system.send_initial_message(introduction)
    
    await system.wait_for_shutdown()

app = VoiceAgentApp(handle_new_call)

if __name__ == "__main__":
    app.run()
