import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # LLM Provider: "groq", "ollama", "cerebras", or "openrouter"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    
    # Groq Configuration (Cloud API - Fast but rate limited)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    
    # Cerebras Configuration (Cloud API - Very fast inference, generous free tier)
    CEREBRAS_API_KEY: str = os.getenv("CEREBRAS_API_KEY", "")
    CEREBRAS_MODEL: str = os.getenv("CEREBRAS_MODEL", "llama-3.3-70b")
    CEREBRAS_API_URL: str = os.getenv("CEREBRAS_API_URL", "https://api.cerebras.ai/v1/chat/completions")
    
    # OpenRouter Configuration (Cloud API - Many models, pay-per-token)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324")
    OPENROUTER_API_URL: str = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
    
    # Ollama Configuration (Local - Unlimited, requires Ollama running)
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    
    # Simulation
    SIMULATION_SPEED: float = float(os.getenv("SIMULATION_SPEED", "5.0"))
    NUM_AGENTS: int = int(os.getenv("NUM_AGENTS", "8"))
    
    # Memory (FAISS)
    MEMORY_PERSIST_DIR: str = os.getenv("MEMORY_PERSIST_DIR", "./data/memories")

settings = Settings()

