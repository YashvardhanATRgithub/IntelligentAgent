import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Groq Configuration (Primary LLM - Fast API)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    
    # Simulation
    SIMULATION_SPEED: float = float(os.getenv("SIMULATION_SPEED", "5.0"))
    NUM_AGENTS: int = int(os.getenv("NUM_AGENTS", "8"))
    
    # Memory (FAISS)
    MEMORY_PERSIST_DIR: str = os.getenv("MEMORY_PERSIST_DIR", "./data/memories")

settings = Settings()
