"""
Memory Store with FAISS Vector Database
Production-ready semantic search for agent memories
"""
import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import json
import os
import hashlib


@dataclass
class Memory:
    """A single memory entry with Stanford-style importance scoring"""
    id: str
    content: str
    memory_type: str = "observation"  # observation, reflection, action, dialogue
    importance: float = 5.0  # 1-10 scale
    timestamp: datetime = field(default_factory=datetime.now)
    timestamp_unix: float = field(default_factory=lambda: datetime.now().timestamp())
    location: str = ""
    related_agents: List[str] = field(default_factory=list)
    embedding: Optional[np.ndarray] = None
    # Information propagation tracking
    source: str = ""  # Who/where this info came from
    propagation_chain: List[str] = field(default_factory=list)  # Chain of who passed info


class MemoryStore:
    """
    Production-ready memory storage using FAISS for vector similarity search.
    Uses TF-IDF based embeddings for semantic matching without heavy ML models.
    """
    
    def __init__(self, persist_dir: str = "./data/memories"):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        
        # FAISS index per agent
        self.indices: Dict[str, faiss.IndexFlatL2] = {}
        self.memories: Dict[str, List[Memory]] = {}
        self.embedding_dim = 128  # Compact but effective
        
        # Vocabulary for TF-IDF style embeddings
        self.vocab: Dict[str, int] = {}
        self.vocab_size = 0
        
        self._load_all()
    
    def _text_to_embedding(self, text: str) -> np.ndarray:
        """Convert text to embedding using hash-based feature extraction"""
        # Simple but effective: hash-based feature extraction
        # This is a proper technique used in production systems
        embedding = np.zeros(self.embedding_dim, dtype=np.float32)
        
        words = text.lower().split()
        for word in words:
            # Hash word to get feature index
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % self.embedding_dim
            # Use word frequency as weight
            embedding[idx] += 1.0
        
        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def _get_agent_file(self, agent_name: str) -> str:
        """Get file path for agent's memories"""
        safe_name = agent_name.lower().replace(" ", "_").replace(".", "")
        return os.path.join(self.persist_dir, f"{safe_name}.json")
    
    def _load_all(self):
        """Load all agent memories from disk"""
        if not os.path.exists(self.persist_dir):
            return
        
        for filename in os.listdir(self.persist_dir):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(self.persist_dir, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    agent_name = data.get('agent_name', filename.replace('.json', ''))
                    self.memories[agent_name] = []
                    
                    # Initialize FAISS index for this agent
                    self.indices[agent_name] = faiss.IndexFlatL2(self.embedding_dim)
                    
                    for m in data.get('memories', []):
                        memory = Memory(
                            id=m['id'],
                            content=m['content'],
                            memory_type=m.get('memory_type', 'observation'),
                            importance=m.get('importance', 5.0),
                            timestamp=datetime.fromisoformat(m.get('timestamp', datetime.now().isoformat())),
                            timestamp_unix=m.get('timestamp_unix', datetime.now().timestamp()),
                            location=m.get('location', ''),
                            related_agents=m.get('related_agents', [])
                        )
                        memory.embedding = self._text_to_embedding(memory.content)
                        self.memories[agent_name].append(memory)
                        
                        # Add to FAISS index
                        self.indices[agent_name].add(memory.embedding.reshape(1, -1))
                        
                except Exception as e:
                    print(f"Error loading memories: {e}")
    
    def _save_agent(self, agent_name: str):
        """Save agent's memories to disk"""
        if agent_name not in self.memories:
            return
        
        filepath = self._get_agent_file(agent_name)
        data = {
            'agent_name': agent_name,
            'memories': [
                {
                    'id': m.id,
                    'content': m.content,
                    'memory_type': m.memory_type,
                    'importance': m.importance,
                    'timestamp': m.timestamp.isoformat(),
                    'timestamp_unix': m.timestamp_unix,
                    'location': m.location,
                    'related_agents': m.related_agents,
                    'source': m.source,
                    'propagation_chain': m.propagation_chain
                }
                for m in self.memories[agent_name][-100:]  # Keep last 100
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_memory(
        self,
        agent_name: str,
        content: str,
        memory_type: str = "observation",
        importance: float = 5.0,
        related_agents: List[str] = None,
        location: str = "",
        source: str = "",
        propagation_chain: List[str] = None
    ) -> str:
        """Add a memory with FAISS indexing and source tracking"""
        # Initialize if needed
        if agent_name not in self.memories:
            self.memories[agent_name] = []
            self.indices[agent_name] = faiss.IndexFlatL2(self.embedding_dim)
        
        memory_id = f"{agent_name}_{datetime.now().timestamp()}"
        
        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            location=location,
            related_agents=related_agents or [],
            source=source,
            propagation_chain=propagation_chain or []
        )
        memory.embedding = self._text_to_embedding(content)
        
        self.memories[agent_name].append(memory)
        self.indices[agent_name].add(memory.embedding.reshape(1, -1))
        
        # Persist every 5 memories
        if len(self.memories[agent_name]) % 5 == 0:
            self._save_agent(agent_name)
        
        return memory_id
    
    def retrieve_memories(
        self,
        agent_name: str,
        query: str,
        limit: int = 5,
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant memories using FAISS similarity search"""
        if agent_name not in self.memories or not self.memories[agent_name]:
            return []
        
        # Get query embedding
        query_embedding = self._text_to_embedding(query)
        
        # FAISS search
        index = self.indices[agent_name]
        k = min(limit * 3, len(self.memories[agent_name]))  # Get more for re-ranking
        
        distances, indices = index.search(query_embedding.reshape(1, -1), k)
        
        current_time = datetime.now().timestamp()
        results = []
        
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(self.memories[agent_name]):
                continue
            
            memory = self.memories[agent_name][idx]
            
            # Filter by type if specified
            if memory_type and memory.memory_type != memory_type:
                continue
            
            # Calculate combined score
            distance = distances[0][i]
            similarity = 1.0 / (1.0 + distance)
            
            hours_ago = (current_time - memory.timestamp_unix) / 3600
            recency = 1.0 / (1.0 + hours_ago * 0.1)
            
            importance_score = memory.importance / 10.0
            
            combined = (similarity * 0.4 + recency * 0.3 + importance_score * 0.3)
            
            results.append({
                "id": memory.id,
                "content": memory.content,
                "memory_type": memory.memory_type,
                "importance": memory.importance,
                "timestamp": memory.timestamp.isoformat(),
                "location": memory.location,
                "related_agents": memory.related_agents,
                "score": combined
            })
        
        # Sort by combined score
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def get_recent_memories(self, agent_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent memories"""
        if agent_name not in self.memories:
            return []
        
        sorted_memories = sorted(
            self.memories[agent_name],
            key=lambda m: m.timestamp_unix,
            reverse=True
        )[:limit]
        
        return [
            {
                "id": m.id,
                "content": m.content,
                "memory_type": m.memory_type,
                "importance": m.importance,
                "timestamp": m.timestamp.isoformat()
            }
            for m in sorted_memories
        ]
    
    def add_reflection(self, agent_name: str, reflection: str, based_on: List[str] = None) -> str:
        """Add high-importance reflection"""
        return self.add_memory(
            agent_name=agent_name,
            content=f"Reflection: {reflection}",
            memory_type="reflection",
            importance=8.0,
            related_agents=based_on
        )
    
    def get_memory_count(self, agent_name: str) -> int:
        """Get total memory count"""
        return len(self.memories.get(agent_name, []))
    
    def save_all(self):
        """Save all memories to disk"""
        for agent_name in self.memories:
            self._save_agent(agent_name)


# Global instance
memory_store = MemoryStore()
