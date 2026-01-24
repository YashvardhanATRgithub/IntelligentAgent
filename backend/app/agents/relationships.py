"""
Relationship Manager - Tracks relationships between agents
Based on Stanford Generative Agents relationship tracking
"""
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Relationship:
    """Relationship between two agents"""
    agent_a: str
    agent_b: str
    strength: int = 50  # 0-100 scale
    sentiment: str = "neutral"  # positive, neutral, negative
    last_interaction: datetime = field(default_factory=datetime.now)
    interaction_count: int = 0
    notes: List[str] = field(default_factory=list)  # Recent interaction summaries


class RelationshipManager:
    """
    Tracks and updates relationships between all agents.
    Relationships are bidirectional and affect agent decision-making.
    """
    
    def __init__(self):
        # Store relationships as {agent_name: {other_agent: Relationship}}
        self.relationships: Dict[str, Dict[str, Relationship]] = {}
        
        # Default relationship strength for colleagues
        self.default_strength = 50
    
    def initialize_relationships(self, agent_names: List[str]):
        """Initialize relationships between all agents"""
        for agent_a in agent_names:
            self.relationships[agent_a] = {}
            for agent_b in agent_names:
                if agent_a != agent_b:
                    self.relationships[agent_a][agent_b] = Relationship(
                        agent_a=agent_a,
                        agent_b=agent_b,
                        strength=self.default_strength
                    )
    
    def get_relationship(self, agent_a: str, agent_b: str) -> Optional[Relationship]:
        """Get relationship between two agents"""
        if agent_a in self.relationships and agent_b in self.relationships[agent_a]:
            return self.relationships[agent_a][agent_b]
        return None
    
    def get_all_relationships(self, agent_name: str) -> Dict[str, Relationship]:
        """Get all relationships for an agent"""
        return self.relationships.get(agent_name, {})
    
    def update_after_interaction(
        self,
        agent_a: str,
        agent_b: str,
        interaction_type: str,  # "talk", "work_together", "help", "conflict"
        sentiment: str = "neutral"  # "positive", "neutral", "negative"
    ):
        """Update relationship after an interaction"""
        # Update A -> B
        rel_ab = self.get_relationship(agent_a, agent_b)
        if rel_ab:
            rel_ab.interaction_count += 1
            rel_ab.last_interaction = datetime.now()
            
            # Adjust strength based on interaction type and sentiment
            if sentiment == "positive":
                rel_ab.strength = min(100, rel_ab.strength + 3)
            elif sentiment == "negative":
                rel_ab.strength = max(0, rel_ab.strength - 5)
            else:
                rel_ab.strength = min(100, rel_ab.strength + 1)  # Neutral still builds familiarity
            
            rel_ab.sentiment = sentiment
        
        # Update B -> A (symmetric relationship building)
        rel_ba = self.get_relationship(agent_b, agent_a)
        if rel_ba:
            rel_ba.interaction_count += 1
            rel_ba.last_interaction = datetime.now()
            
            if sentiment == "positive":
                rel_ba.strength = min(100, rel_ba.strength + 3)
            elif sentiment == "negative":
                rel_ba.strength = max(0, rel_ba.strength - 5)
            else:
                rel_ba.strength = min(100, rel_ba.strength + 1)
            
            rel_ba.sentiment = sentiment
    
    def get_closest_relationships(self, agent_name: str, limit: int = 3) -> List[str]:
        """Get the agents this agent has the strongest relationship with"""
        relationships = self.get_all_relationships(agent_name)
        sorted_rels = sorted(
            relationships.items(),
            key=lambda x: x[1].strength,
            reverse=True
        )
        return [name for name, _ in sorted_rels[:limit]]
    
    def describe_relationship(self, agent_a: str, agent_b: str) -> str:
        """Get a text description of the relationship for prompts"""
        rel = self.get_relationship(agent_a, agent_b)
        if not rel:
            return f"{agent_b}: Unknown"
        
        strength = rel.strength
        if strength >= 80:
            desc = "close friend"
        elif strength >= 60:
            desc = "friendly colleague"
        elif strength >= 40:
            desc = "acquaintance"
        elif strength >= 20:
            desc = "distant colleague"
        else:
            desc = "strained relationship"
        
        return f"{agent_b}: {desc} (strength: {strength})"
    
    def to_dict(self, agent_name: str) -> Dict[str, Dict]:
        """Export relationships as dictionary for API"""
        result = {}
        for other, rel in self.get_all_relationships(agent_name).items():
            result[other] = {
                "strength": rel.strength,
                "sentiment": rel.sentiment,
                "interaction_count": rel.interaction_count,
                "last_interaction": rel.last_interaction.isoformat()
            }
        return result
    
    def get_relationship_scores(self, agent_name: str) -> Dict[str, float]:
        """
        Get relationship scores as a simple dict for attention prioritization.
        Returns normalized scores (0-1 range) for use in perceive module.
        """
        scores = {}
        for other, rel in self.get_all_relationships(agent_name).items():
            # Normalize strength from 0-100 to 0-1
            scores[other] = rel.strength / 100.0
        return scores


# Global relationship manager instance
relationship_manager = RelationshipManager()
