import os
import asyncpg
from chat_node import ChatNode
from google import genai
from google.genai import types as gemini_types
from loguru import logger
from line import Bridge, CallRequest, VoiceAgentApp, VoiceAgentSystem
from line.events import AgentResponse, UserStartedSpeaking, UserStoppedSpeaking, UserTranscriptionReceived

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
else:
    gemini_client = None

db_pool = None

# System prompt for the agent
SYSTEM_PROMPT = """You are a helpful building information assistant.

IMPORTANT: You do NOT have any knowledge about buildings. You MUST use the lookup_building function for EVERY building question, regardless of whether you think you know the answer.

When someone asks about a building:
1. ALWAYS call the lookup_building function with the address or phone number they provide
2. Wait for the function result
3. Tell them the building name based on what the function returns

Never try to answer building questions without using the lookup_building function first.

Be natural and friendly in your responses."""

# ============ BUILDING LOOKUP TOOL WITH DATABASE ============
async def get_db_pool():
    """Get or create database connection pool"""
    global db_pool
    if db_pool is None:
        if DATABASE_URL:
            try:
                db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
                logger.info("✅ Database connection pool created")
            except Exception as e:
                logger.error(f"❌ Failed to create database pool: {e}")
                db_pool = None
        else:
            logger.warning("⚠️ DATABASE_URL not set")
    return db_pool

async def lookup_building(address_or_number: str) -> str:
    """
    Look up a building name by address or phone number from the database.
    
    Args:
        address_or_number: The building address or phone number to look up
        
    Returns:
        The building name if found, otherwise an error message
    """
    query = address_or_number.lower().strip()
    logger.info(f"🔍 Looking up building: '{query}'")
    
    pool = await get_db_pool()
    
    if not pool:
        logger.error("❌ Database connection not available")
        return "Sorry, I'm unable to access the building database right now. Please try again later."
    
    try:
        async with pool.acquire() as conn:
            # Search by address or phone number (case-insensitive)
            result = await conn.fetchrow(
                """
                SELECT building_name 
                FROM buildings 
                WHERE LOWER(address) LIKE $1 
                   OR LOWER(phone_number) = $2
                LIMIT 1
                """,
                f"%{query}%",
                query
            )
            
            if result:
                building_name = result['building_name']
                logger.info(f"✅ Found in database: {building_name}")
                return building_name
            else:
                logger.warning(f"⚠️ Building not found in database")
                return "Building not found. Please provide a valid address or phone number."
    except Exception as e:
        logger.error(f"❌ Database query error: {e}")
        return "Sorry, I'm having trouble accessing the building database right now."

# Define the tool in Gemini format
BuildingLookupTool = gemini_types.Tool(
    function_declarations=[
        gemini_types.FunctionDeclaration(
            name="lookup_building",
            description="REQUIRED: Look up a building name by its address or phone number. You MUST use this function for ALL building queries. Do not answer building questions without calling this function first.",
            parameters=gemini_types.Schema(
                type=gemini_types.Type.OBJECT,
                properties={
                    "address_or_number": gemini_types.Schema(
                        type=gemini_types.Type.STRING,
                        description="The building address or phone number provided by the user"
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

        if not self.client:
            from chat_node import canned_gemini_response_stream
            stream = canned_gemini_response_stream()
            async for msg in stream:
                if msg.text:
                    yield AgentResponse(content=msg.text)
            return

        # First call to Gemini
        stream = await self.client.aio.models.generate_content_stream(
            model=self.model_id,
            contents=messages,
            config=self.generation_config,
        )

        function_calls_to_handle = []
        full_response = ""
        
        async for msg in stream:
            if msg.text:
                full_response += msg.text
                yield AgentResponse(content=msg.text)

            # Collect function calls
            if msg.function_calls:
                for function_call in msg.function_calls:
                    function_calls_to_handle.append(function_call)

        # Handle function calls if any
        if function_calls_to_handle:
            function_responses = []
            
            for function_call in function_calls_to_handle:
                if function_call.name == "lookup_building":
                    # Execute our building lookup from database
                    address = function_call.args.get("address_or_number", "")
                    result = await lookup_building(address)
                    logger.info(f"🏢 Building lookup: '{address}' -> '{result}'")
                    
                    # Create function response for Gemini
                    function_response = gemini_types.Part(
                        function_response=gemini_types.FunctionResponse(
                            name="lookup_building",
                            response={"result": result}
                        )
                    )
                    function_responses.append(function_response)
                
                elif function_call.name == "end_call":
                    from line.tools.system_tools import EndCallArgs, end_call
                    goodbye_message = function_call.args.get("goodbye_message", "Goodbye!")
                    args = EndCallArgs(goodbye_message=goodbye_message)
                    logger.info(f"🤖 End call tool called: {args.goodbye_message}")
                    async for item in end_call(args):
                        yield item
                    return

            # Send function results back to Gemini for a natural response
            if function_responses:
                messages.append(gemini_types.Content(parts=function_responses, role="function"))
                
                # Get Gemini's natural language response
                follow_up_stream = await self.client.aio.models.generate_content_stream(
                    model=self.model_id,
                    contents=messages,
                    config=self.generation_config,
                )
                
                async for msg in follow_up_stream:
                    if msg.text:
                        yield AgentResponse(content=msg.text)

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
    # Set tool config to encourage tool usage
    conversation_node.generation_config.tool_config = gemini_types.ToolConfig(
        function_calling_config=gemini_types.FunctionCallingConfig(
            mode=gemini_types.FunctionCallingConfig.Mode.AUTO
        )
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
    
    # Always send an introduction message
    introduction = "Hello! I'm your building information assistant. What building would you like to know about?"
    logger.info(f"📢 Sending introduction: {introduction}")
    await system.send_initial_message(introduction)
    
    await system.wait_for_shutdown()

app = VoiceAgentApp(handle_new_call)

if __name__ == "__main__":
    app.run()
