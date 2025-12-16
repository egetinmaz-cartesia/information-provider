from fastapi import FastAPI
from dotenv import load_dotenv
from line import VoiceAgentSystem
from pydantic import BaseModel

load_dotenv()

app = FastAPI()

# Initialize the voice agent system
agent = VoiceAgentSystem(
    agent_id="agent_7CcsA878NH514PoBs6rF5z"
)

@app.on_event("startup")
async def on_startup():
    await agent.start()

@app.on_event("shutdown")
async def on_shutdown():
    await agent.stop()

# -------- Context Model --------

class ContextVariables(BaseModel):
    building_address: str
    building_number: str
    building_name: str

# -------- Start Session Endpoint --------

@app.post("/start")
async def start_conversation(context: ContextVariables):
    """
    Starts a new conversation session with injected context variables.
    """
    session = await agent.start_session(
        context_variables=context.dict()
    )

    return {
        "status": "started",
        "session_id": session.id
    }

@app.get("/health")
async def health():
    return {"status": "ok"}
