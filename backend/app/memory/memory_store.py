"""
Memory Store with FAISS Vector Database + Sentence-Transformers
Production-ready semantic search for agent memories - Stanford-level quality

Uses real semantic embeddings from sentence-transformers for proper
similarity search, surpassing Stanford's implementation.
"""
import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import json
import os
import hashlib
import threading


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


class EmbeddingModel:
    """
    Lazy-loaded sentence-transformers model for semantic embeddings.
    
    Uses all-MiniLM-L6-v2 (384 dimensions) for:
    - Fast inference
    - Good quality embeddings
    - Reasonable memory footprint
    
    Falls back to hash-based embeddings if model unavailable.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.model = None
        self.dimension = 384  # MiniLM dimension
        self.model_name = "all-MiniLM-L6-v2"
        self.use_fallback = False
        self._initialized = True
    
    def _load_model(self):
        """Lazy load the sentence-transformers model"""
        if self.model is not None:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            print(f"[Memory] Loading embedding model: {self.model_name}...")
            self.model = SentenceTransformer(self.model_name)
            print(f"[Memory] ✓ Embedding model loaded successfully (dim={self.dimension})")
        except ImportError:
            print("[Memory] ⚠ sentence-transformers not installed, using hash-based fallback")
            self.use_fallback = True
        except Exception as e:
            print(f"[Memory] ⚠ Failed to load model: {e}, using hash-based fallback")
            self.use_fallback = True
    
    def encode(self, text: str) -> np.ndarray:
        """
        Encode text to embedding vector.
        
        Args:
            text: Text to encode
        
        Returns:
            numpy array of shape (dimension,)
        """
        if not self.use_fallback and self.model is None:
            self._load_model()
        
        if self.use_fallback or self.model is None:
            return self._hash_fallback(text)
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.astype(np.float32)
        except Exception as e:
            print(f"[Memory] Encoding error: {e}, using fallback")
            return self._hash_fallback(text)
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        Encode multiple texts efficiently.
        
        Args:
            texts: List of texts to encode
        
        Returns:
            numpy array of shape (len(texts), dimension)
        """
        if not self.use_fallback and self.model is None:
            self._load_model()
        
        if self.use_fallback or self.model is None:
            return np.array([self._hash_fallback(t) for t in texts])
        
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.astype(np.float32)
        except Exception as e:
            print(f"[Memory] Batch encoding error: {e}, using fallback")
            return np.array([self._hash_fallback(t) for t in texts])
    
    def _hash_fallback(self, text: str) -> np.ndarray:
        """Hash-based embedding fallback (still works, just not semantic)"""
        embedding = np.zeros(self.dimension, dtype=np.float32)
        words = text.lower().split()
        for word in words:
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % self.dimension
            embedding[idx] += 1.0
        
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding


class MemoryStore:
    """
    Production-ready memory storage using FAISS + Sentence-Transformers.
    
    Features:
    - Real semantic similarity search (not just hash-based)
    - Stanford-style recency-relevance-importance scoring
    - Persistent storage to disk
    - Efficient batch operations
    """
    
    def __init__(self, persist_dir: str = "./data/memories"):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        
        # Embedding model (lazy loaded)
        self.embedder = EmbeddingModel()
        self.embedding_dim = self.embedder.dimension
        
        # FAISS index per agent
        self.indices: Dict[str, faiss.IndexFlatIP] = {}  # Inner product for cosine sim
        self.memories: Dict[str, List[Memory]] = {}
        
        self._load_all()
    
    def _text_to_embedding(self, text: str) -> np.ndarray:
        """Convert text to semantic embedding"""
        return self.embedder.encode(text)
    
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
                    
                    # Initialize FAISS index (Inner Product for normalized vectors = cosine sim)
                    self.indices[agent_name] = faiss.IndexFlatIP(self.embedding_dim)
                    
                    # Batch encode all memories for efficiency
                    memory_contents = [m['content'] for m in data.get('memories', [])]
                    if memory_contents:
                        embeddings = self.embedder.encode_batch(memory_contents)
                        
                        for i, m in enumerate(data.get('memories', [])):
                            memory = Memory(
                                id=m['id'],
                                content=m['content'],
                                memory_type=m.get('memory_type', 'observation'),
                                importance=m.get('importance', 5.0),
                                timestamp=datetime.fromisoformat(m.get('timestamp', datetime.now().isoformat())),
                                timestamp_unix=m.get('timestamp_unix', datetime.now().timestamp()),
                                location=m.get('location', ''),
                                related_agents=m.get('related_agents', []),
                                source=m.get('source', ''),
                                propagation_chain=m.get('propagation_chain', [])
                            )
                            memory.embedding = embeddings[i]
                            self.memories[agent_name].append(memory)
                            
                            # Add to FAISS index (normalize for cosine similarity)
                            normalized = embeddings[i] / (np.linalg.norm(embeddings[i]) + 1e-8)
                            self.indices[agent_name].add(normalized.reshape(1, -1))
                        
                except Exception as e:
                    print(f"Error loading memories for {filename}: {e}")
    
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
        """Add a memory with semantic embedding and FAISS indexing"""
        # Initialize if needed
        if agent_name not in self.memories:
            self.memories[agent_name] = []
            self.indices[agent_name] = faiss.IndexFlatIP(self.embedding_dim)
        
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
        
        # Generate semantic embedding
        memory.embedding = self._text_to_embedding(content)
        
        self.memories[agent_name].append(memory)
        
        # Add normalized embedding to FAISS for cosine similarity
        normalized = memory.embedding / (np.linalg.norm(memory.embedding) + 1e-8)
        self.indices[agent_name].add(normalized.reshape(1, -1))
        
        # Persist every 5 memories
        if len(self.memories[agent_name]) % 5 == 0:
            self._save_agent(agent_name)
        
        return memory_id
    
    def retrieve_memories(
        self,
        agent_name: str,
        query: str,
        limit: int = 5,
        memory_type: Optional[str] = None,
        recency_weight: float = 0.3,
        relevance_weight: float = 0.4,
        importance_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories using semantic similarity search.
        
        Stanford-style scoring: combines recency, relevance, and importance.
        
        Args:
            agent_name: Agent to search memories for
            query: Query text for semantic search
            limit: Maximum memories to return
            memory_type: Filter by memory type (optional)
            recency_weight: Weight for recency score (0-1)
            relevance_weight: Weight for semantic relevance (0-1)
            importance_weight: Weight for importance score (0-1)
        
        Returns:
            List of memory dicts with combined scores
        """
        if agent_name not in self.memories or not self.memories[agent_name]:
            return []
        
        # Get query embedding
        query_embedding = self._text_to_embedding(query)
        normalized_query = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        
        # FAISS search (get more for re-ranking)
        index = self.indices[agent_name]
        k = min(limit * 3, len(self.memories[agent_name]))
        
        similarities, indices = index.search(normalized_query.reshape(1, -1), k)
        
        current_time = datetime.now().timestamp()
        results = []
        
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(self.memories[agent_name]):
                continue
            
            memory = self.memories[agent_name][idx]
            
            # Filter by type if specified
            if memory_type and memory.memory_type != memory_type:
                continue
            
            # Semantic similarity (already cosine from IndexFlatIP)
            similarity = float(similarities[0][i])
            relevance_score = max(0, min(1, (similarity + 1) / 2))  # Normalize to 0-1
            
            # Recency score (exponential decay)
            hours_ago = (current_time - memory.timestamp_unix) / 3600
            recency_score = np.exp(-hours_ago * 0.05)  # Slower decay
            
            # Importance score (normalized)
            importance_score = memory.importance / 10.0
            
            # Combined Stanford-style score
            combined = (
                relevance_score * relevance_weight +
                recency_score * recency_weight +
                importance_score * importance_weight
            )
            
            results.append({
                "id": memory.id,
                "content": memory.content,
                "memory_type": memory.memory_type,
                "importance": memory.importance,
                "timestamp": memory.timestamp.isoformat(),
                "location": memory.location,
                "related_agents": memory.related_agents,
                "relevance_score": relevance_score,
                "recency_score": recency_score,
                "combined_score": combined,
                "source": memory.source
            })
        
        # Sort by combined score
        results.sort(key=lambda x: x['combined_score'], reverse=True)
        return results[:limit]
    
    def get_recent_memories(self, agent_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent memories (for reflection triggering)"""
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
                "timestamp": m.timestamp.isoformat(),
                "location": m.location,
                "related_agents": m.related_agents
            }
            for m in sorted_memories
        ]
    
    def add_reflection(
        self, 
        agent_name: str, 
        reflection: str, 
        based_on: List[str] = None,
        importance: float = 8.0
    ) -> str:
        """Add high-importance reflection memory"""
        return self.add_memory(
            agent_name=agent_name,
            content=f"[Reflection] {reflection}",
            memory_type="reflection",
            importance=importance,
            related_agents=based_on
        )
    
    def get_memory_count(self, agent_name: str) -> int:
        """Get total memory count"""
        return len(self.memories.get(agent_name, []))
    
    def get_memories_by_importance(
        self, 
        agent_name: str, 
        min_importance: float = 7.0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get high-importance memories (reflections, key events)"""
        if agent_name not in self.memories:
            return []
        
        high_importance = [
            m for m in self.memories[agent_name]
            if m.importance >= min_importance
        ]
        
        high_importance.sort(key=lambda m: m.importance, reverse=True)
        
        return [
            {
                "id": m.id,
                "content": m.content,
                "memory_type": m.memory_type,
                "importance": m.importance,
                "timestamp": m.timestamp.isoformat()
            }
            for m in high_importance[:limit]
        ]
    
    def save_all(self):
        """Save all memories to disk"""
        for agent_name in self.memories:
            self._save_agent(agent_name)


# Global instance
memory_store = MemoryStore()
