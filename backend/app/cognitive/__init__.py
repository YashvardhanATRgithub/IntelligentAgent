"""
Cognitive Modules for Generative Agents

This package contains the higher-level cognitive functions:
- Conversation: Multi-turn dialogue with turn-taking
- More modules to come (perception, emotion, etc.)
"""
from .converse import ConversationChoreographer, ConversationContext, ConversationResult

__all__ = [
    "ConversationChoreographer",
    "ConversationContext",
    "ConversationResult",
]
