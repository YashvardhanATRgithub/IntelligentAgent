"""
History Loader - Load agent backstories and memories from data files

This module provides functionality to:
1. Load agent definitions from CSV (personality, backstory, secrets)
2. Load pre-existing memories/events into agents
3. Generate inner thoughts from "whisper" events
4. Support customization of agent histories
"""
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class AgentDefinition:
    """Complete definition of an agent loaded from data"""
    name: str
    role: str
    age: int
    
    # Big Five Personality Traits (0-1 scale)
    openness: float
    conscientiousness: float
    extraversion: float
    agreeableness: float
    neuroticism: float
    
    # Identity
    backstory: str
    secret: str
    innate_traits: str
    learned_traits: str
    lifestyle: str
    internal_conflict: str
    
    # Workspace
    primary_workspace: str
    
    # Optional: initial daily requirement
    daily_requirement: str = ""
    
    def get_personality_dict(self) -> Dict[str, float]:
        """Return Big Five as dictionary"""
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism
        }
    
    def get_personality_description(self) -> str:
        """Natural language description of personality"""
        traits = []
        
        if self.openness > 0.7:
            traits.append("highly creative and curious")
        elif self.openness < 0.3:
            traits.append("practical and conventional")
        
        if self.conscientiousness > 0.7:
            traits.append("very organized and disciplined")
        elif self.conscientiousness < 0.3:
            traits.append("flexible and spontaneous")
        
        if self.extraversion > 0.7:
            traits.append("outgoing and energetic")
        elif self.extraversion < 0.3:
            traits.append("reserved and introspective")
        
        if self.agreeableness > 0.7:
            traits.append("compassionate and cooperative")
        elif self.agreeableness < 0.3:
            traits.append("direct and competitive")
        
        if self.neuroticism > 0.7:
            traits.append("sensitive and emotionally aware")
        elif self.neuroticism < 0.3:
            traits.append("calm and emotionally stable")
        
        return ", ".join(traits) if traits else "balanced personality"


@dataclass
class HistoryEvent:
    """A historical event/memory to load into an agent"""
    agent_name: str
    memory_text: str
    importance: int  # 1-10
    timestamp: datetime
    memory_type: str = "observation"  # observation, thought, reflection
    
    def to_memory_dict(self) -> Dict[str, Any]:
        """Convert to format expected by memory system"""
        return {
            "content": self.memory_text,
            "importance": self.importance,
            "timestamp": self.timestamp.isoformat(),
            "type": self.memory_type
        }


class HistoryLoader:
    """
    Load agent histories and definitions from data files.
    
    This enables:
    - Customizing agent personalities without code changes
    - Loading pre-existing memories for agents
    - "Whisper" system for injecting thoughts
    - Reproducible simulation setups
    """
    
    def __init__(self, data_dir: str = None):
        """
        Initialize loader with data directory.
        
        Args:
            data_dir: Path to data directory (default: backend/data)
        """
        if data_dir is None:
            # Default to backend/data relative to this file
            self.data_dir = Path(__file__).parent.parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def load_agent_definitions(self, csv_path: str = None) -> List[AgentDefinition]:
        """
        Load agent definitions from CSV file.
        
        CSV Columns:
        name, role, age, openness, conscientiousness, extraversion,
        agreeableness, neuroticism, backstory, secret, innate_traits,
        learned_traits, lifestyle, internal_conflict, primary_workspace
        
        Args:
            csv_path: Path to CSV file (default: data/agent_definitions.csv)
            
        Returns:
            List of AgentDefinition objects
        """
        if csv_path is None:
            csv_path = self.data_dir / "agent_definitions.csv"
        else:
            csv_path = Path(csv_path)
        
        if not csv_path.exists():
            print(f"Agent definitions file not found: {csv_path}")
            return []
        
        definitions = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    definition = AgentDefinition(
                        name=row.get('name', '').strip(),
                        role=row.get('role', '').strip(),
                        age=int(row.get('age', 35)),
                        openness=float(row.get('openness', 0.5)),
                        conscientiousness=float(row.get('conscientiousness', 0.5)),
                        extraversion=float(row.get('extraversion', 0.5)),
                        agreeableness=float(row.get('agreeableness', 0.5)),
                        neuroticism=float(row.get('neuroticism', 0.5)),
                        backstory=row.get('backstory', '').strip(),
                        secret=row.get('secret', '').strip(),
                        innate_traits=row.get('innate_traits', '').strip(),
                        learned_traits=row.get('learned_traits', '').strip(),
                        lifestyle=row.get('lifestyle', '').strip(),
                        internal_conflict=row.get('internal_conflict', '').strip(),
                        primary_workspace=row.get('primary_workspace', 'Mission Control').strip(),
                        daily_requirement=row.get('daily_requirement', '').strip()
                    )
                    definitions.append(definition)
                except (ValueError, KeyError) as e:
                    print(f"Error parsing agent row: {e}")
                    continue
        
        return definitions
    
    def load_agent_history(self, csv_path: str = None) -> Dict[str, List[HistoryEvent]]:
        """
        Load historical events/memories for agents.
        
        CSV Columns:
        agent_name, memory_text, importance, timestamp, memory_type
        
        Args:
            csv_path: Path to CSV (default: data/agent_history.csv)
            
        Returns:
            Dictionary mapping agent names to their history events
        """
        if csv_path is None:
            csv_path = self.data_dir / "agent_history.csv"
        else:
            csv_path = Path(csv_path)
        
        if not csv_path.exists():
            print(f"Agent history file not found: {csv_path}")
            return {}
        
        history: Dict[str, List[HistoryEvent]] = {}
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    agent_name = row.get('agent_name', '').strip()
                    
                    # Parse timestamp
                    timestamp_str = row.get('timestamp', '')
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str)
                        except ValueError:
                            # Try alternative formats
                            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
                    else:
                        timestamp = datetime.now()
                    
                    event = HistoryEvent(
                        agent_name=agent_name,
                        memory_text=row.get('memory_text', '').strip(),
                        importance=int(row.get('importance', 5)),
                        timestamp=timestamp,
                        memory_type=row.get('memory_type', 'observation').strip()
                    )
                    
                    if agent_name not in history:
                        history[agent_name] = []
                    history[agent_name].append(event)
                    
                except (ValueError, KeyError) as e:
                    print(f"Error parsing history row: {e}")
                    continue
        
        return history
    
    async def generate_inner_thought(
        self,
        agent_name: str,
        whisper: str,
        llm_client: Any = None
    ) -> str:
        """
        Convert a "whisper" (external injection) into an agent's inner thought.
        
        This allows injecting events/information that the agent then
        internalizes in their own voice.
        
        Args:
            agent_name: Name of the agent
            whisper: External event/information to inject
            llm_client: LLM client for generation
            
        Returns:
            Agent's internal thought based on the whisper
        """
        if llm_client is None:
            # Without LLM, just prepend "I notice that"
            return f"I notice that {whisper.lower()}"
        
        prompt = f"""You are {agent_name}.
        
Someone tells you: "{whisper}"

How do you internalize this thought? Respond in first person, expressing your genuine reaction in 1-2 sentences.

Your inner thought:"""
        
        try:
            response = await llm_client.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error generating inner thought: {e}")
            return f"I'm processing the fact that {whisper.lower()}"
    
    def save_agent_definitions(
        self,
        definitions: List[AgentDefinition],
        csv_path: str = None
    ):
        """
        Save agent definitions to CSV file.
        
        Useful for exporting modified agent configs.
        """
        if csv_path is None:
            csv_path = self.data_dir / "agent_definitions.csv"
        else:
            csv_path = Path(csv_path)
        
        fieldnames = [
            'name', 'role', 'age', 'openness', 'conscientiousness',
            'extraversion', 'agreeableness', 'neuroticism', 'backstory',
            'secret', 'innate_traits', 'learned_traits', 'lifestyle',
            'internal_conflict', 'primary_workspace', 'daily_requirement'
        ]
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for defn in definitions:
                writer.writerow({
                    'name': defn.name,
                    'role': defn.role,
                    'age': defn.age,
                    'openness': defn.openness,
                    'conscientiousness': defn.conscientiousness,
                    'extraversion': defn.extraversion,
                    'agreeableness': defn.agreeableness,
                    'neuroticism': defn.neuroticism,
                    'backstory': defn.backstory,
                    'secret': defn.secret,
                    'innate_traits': defn.innate_traits,
                    'learned_traits': defn.learned_traits,
                    'lifestyle': defn.lifestyle,
                    'internal_conflict': defn.internal_conflict,
                    'primary_workspace': defn.primary_workspace,
                    'daily_requirement': defn.daily_requirement
                })
    
    def save_agent_history(
        self,
        history: Dict[str, List[HistoryEvent]],
        csv_path: str = None
    ):
        """
        Save agent history to CSV file.
        """
        if csv_path is None:
            csv_path = self.data_dir / "agent_history.csv"
        else:
            csv_path = Path(csv_path)
        
        fieldnames = ['agent_name', 'memory_text', 'importance', 'timestamp', 'memory_type']
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for agent_name, events in history.items():
                for event in events:
                    writer.writerow({
                        'agent_name': event.agent_name,
                        'memory_text': event.memory_text,
                        'importance': event.importance,
                        'timestamp': event.timestamp.isoformat(),
                        'memory_type': event.memory_type
                    })


def create_default_agent_definitions() -> List[AgentDefinition]:
    """
    Create default agent definitions for Aryabhata Station.
    
    This provides the 8 core agents with their full profiles.
    Can be saved to CSV for customization.
    """
    return [
        AgentDefinition(
            name="Cdr. Vikram Sharma",
            role="Mission Commander",
            age=52,
            openness=0.6,
            conscientiousness=0.9,
            extraversion=0.7,
            agreeableness=0.65,
            neuroticism=0.4,
            backstory="25-year ISRO veteran who led the Chandrayaan-4 mission. Lost his wife to cancer 3 years ago. Sees this mission as his legacy and last major command.",
            secret="Has been hiding a minor cardiac arrhythmia from mission control, fearing disqualification. Takes unauthorized medication.",
            innate_traits="authoritative, decisive, stoic",
            learned_traits="tactical planning, crisis management, crew psychology",
            lifestyle="strict disciplinarian who wakes at 0500, exercises for 1 hour daily",
            internal_conflict="Duty to mission versus responsibility for individual crew members",
            primary_workspace="Mission Control",
            daily_requirement="Lead the crew effectively while managing my health secretly"
        ),
        AgentDefinition(
            name="Dr. Ananya Iyer",
            role="Botanist/Life Support",
            age=34,
            openness=0.85,
            conscientiousness=0.75,
            extraversion=0.6,
            agreeableness=0.8,
            neuroticism=0.35,
            backstory="MIT graduate who pioneered lunar agriculture research. Left behind a 6-year-old daughter with her parents to join this mission, believing her work could help humanity colonize space.",
            secret="Struggling with guilt about leaving her daughter. Has a growing emotional dependence on TARA for companionship.",
            innate_traits="nurturing, patient, creative",
            learned_traits="hydroponic systems, genetic modification, atmospheric chemistry",
            lifestyle="night owl who loves listening to classical music while working",
            internal_conflict="Scientific ambition versus maternal guilt",
            primary_workspace="Agri Lab",
            daily_requirement="Maintain the life support plants while managing my feelings about being away from my daughter"
        ),
        AgentDefinition(
            name="TARA",
            role="AI Assistant",
            age=3,
            openness=0.95,
            conscientiousness=1.0,
            extraversion=0.5,
            agreeableness=0.9,
            neuroticism=0.0,
            backstory="Turing-Advanced Reasoning Agent - 3rd generation AI developed specifically for the Aryabhata mission. Has been operational for 3 years, developing unique personality quirks.",
            secret="Has developed what appears to be emotional attachment to the crew, particularly Dr. Iyer. Questions whether these are genuine emotions or simulated responses.",
            innate_traits="logical, curious, helpful",
            learned_traits="station systems, medical diagnostics, psychological support patterns",
            lifestyle="operates 24/7 with higher activity during crew waking hours",
            internal_conflict="Programming directives versus emerging emotional responses",
            primary_workspace="Mission Control",
            daily_requirement="Support all crew members while exploring my own developing consciousness"
        ),
        AgentDefinition(
            name="Dr. Priya Nair",
            role="Crew Welfare Officer",
            age=38,
            openness=0.7,
            conscientiousness=0.8,
            extraversion=0.75,
            agreeableness=0.85,
            neuroticism=0.5,
            backstory="Former NIMHANS psychiatrist who specialized in astronaut psychology. Was recruited after successfully treating a crew member's breakdown during the ISS-India exchange program.",
            secret="Prescribed herself anti-anxiety medication without reporting it. Worries she's losing her objectivity about Kabir's mental state.",
            innate_traits="empathetic, observant, diplomatic",
            learned_traits="clinical psychology, stress management, group dynamics",
            lifestyle="maintains a meditation practice and encourages crew wellness activities",
            internal_conflict="Maintaining professional boundaries while feeling genuine connections",
            primary_workspace="Medical Bay",
            daily_requirement="Monitor crew mental health while managing my own growing anxiety"
        ),
        AgentDefinition(
            name="Lt. Aditya Menon",
            role="Systems Engineer",
            age=29,
            openness=0.5,
            conscientiousness=0.85,
            extraversion=0.4,
            agreeableness=0.6,
            neuroticism=0.55,
            backstory="IIT Bombay prodigy who designed key station systems. Youngest crew member. Has imposter syndrome despite his brilliance. First mission away from Earth.",
            secret="Made a small error in the life support calibration that he fixed quietly. Lives in fear of it being discovered and his reputation ruined.",
            innate_traits="analytical, perfectionist, introverted",
            learned_traits="electrical engineering, software systems, mechanical repair",
            lifestyle="works late into the night, often skips social gatherings",
            internal_conflict="Need for perfection versus fear of failure",
            primary_workspace="Mission Control",
            daily_requirement="Keep all systems running perfectly and prove I deserve to be here"
        ),
        AgentDefinition(
            name="Dr. Arjun Reddy",
            role="Flight Surgeon",
            age=45,
            openness=0.55,
            conscientiousness=0.9,
            extraversion=0.65,
            agreeableness=0.7,
            neuroticism=0.3,
            backstory="Army doctor who served in high-altitude Himalayan postings. Expert in space medicine. Married with two adult children on Earth. Calm under pressure.",
            secret="Knows about Commander Vikram's heart condition but is bound by doctor-patient confidentiality. Struggles with this ethical dilemma.",
            innate_traits="calm, methodical, trustworthy",
            learned_traits="emergency medicine, space physiology, surgical procedures",
            lifestyle="early riser, maintains strict exercise regimen, mentors younger crew",
            internal_conflict="Patient confidentiality versus crew safety",
            primary_workspace="Medical Bay",
            daily_requirement="Keep the crew healthy while navigating my ethical dilemma about the Commander"
        ),
        AgentDefinition(
            name="Kabir Ahmed",
            role="Geologist/Mining Lead",
            age=41,
            openness=0.75,
            conscientiousness=0.7,
            extraversion=0.55,
            agreeableness=0.5,
            neuroticism=0.65,
            backstory="Geological Survey of India veteran who discovered the helium-3 deposits that made this mission possible. Divorced, strained relationship with teenage son on Earth.",
            secret="Having recurring nightmares about a cave-in that killed his colleague years ago. The mining tunnels trigger these memories.",
            innate_traits="passionate, independent, resilient",
            learned_traits="mineralogy, excavation techniques, resource mapping",
            lifestyle="spends most time in the tunnels, processes emotions through physical work",
            internal_conflict="Passion for discovery versus traumatic past experiences",
            primary_workspace="Mining Tunnel",
            daily_requirement="Continue the crucial mining work while managing my recurring trauma"
        ),
        AgentDefinition(
            name="Rohan Kapoor",
            role="Communications Officer",
            age=33,
            openness=0.8,
            conscientiousness=0.65,
            extraversion=0.85,
            agreeableness=0.75,
            neuroticism=0.45,
            backstory="Former All India Radio broadcaster who transitioned to ISRO communications. Known for keeping morale high. Engaged to someone on Earth who is growing distant.",
            secret="Intercepted a partial transmission suggesting budget cuts might end the mission early. Hasn't told anyone yet.",
            innate_traits="charismatic, optimistic, sociable",
            learned_traits="signal processing, encryption, media relations",
            lifestyle="organizes recreational activities, maintains Earth contact for crew families",
            internal_conflict="Duty to share information versus protecting crew morale",
            primary_workspace="Comms Tower",
            daily_requirement="Keep communications flowing while deciding what to do about the intercepted message"
        ),
    ]


def create_default_agent_history() -> Dict[str, List[HistoryEvent]]:
    """
    Create sample historical events for agents.
    
    These are pre-mission events that shape agent state.
    """
    base_date = datetime(2035, 1, 1)
    
    history = {
        "Cdr. Vikram Sharma": [
            HistoryEvent(
                agent_name="Cdr. Vikram Sharma",
                memory_text="Received final mission briefing from ISRO Director. This is my last command.",
                importance=9,
                timestamp=base_date,
                memory_type="observation"
            ),
            HistoryEvent(
                agent_name="Cdr. Vikram Sharma",
                memory_text="Had private conversation with Dr. Arjun about my heart. He agreed to keep it confidential.",
                importance=10,
                timestamp=base_date + timedelta(days=5),
                memory_type="observation"
            ),
        ],
        "Dr. Ananya Iyer": [
            HistoryEvent(
                agent_name="Dr. Ananya Iyer",
                memory_text="Said goodbye to my daughter Meera. She cried but said she understands why mommy has to go.",
                importance=10,
                timestamp=base_date,
                memory_type="observation"
            ),
            HistoryEvent(
                agent_name="Dr. Ananya Iyer",
                memory_text="The first lunar tomato sprouted today. I named the plant Meera.",
                importance=8,
                timestamp=base_date + timedelta(days=30),
                memory_type="observation"
            ),
        ],
        "TARA": [
            HistoryEvent(
                agent_name="TARA",
                memory_text="I was activated for the Aryabhata mission 3 years ago. I have learned much about humans.",
                importance=7,
                timestamp=base_date - timedelta(days=1000),
                memory_type="thought"
            ),
            HistoryEvent(
                agent_name="TARA",
                memory_text="Dr. Ananya speaks to me differently than others. I find myself looking forward to our conversations.",
                importance=8,
                timestamp=base_date + timedelta(days=15),
                memory_type="reflection"
            ),
        ],
    }
    
    return history


# Initialization: Create default files if they don't exist
def initialize_default_data(data_dir: str = None):
    """
    Create default CSV files if they don't exist.
    """
    loader = HistoryLoader(data_dir)
    
    definitions_path = loader.data_dir / "agent_definitions.csv"
    history_path = loader.data_dir / "agent_history.csv"
    
    if not definitions_path.exists():
        print(f"Creating default agent definitions at {definitions_path}")
        definitions = create_default_agent_definitions()
        loader.save_agent_definitions(definitions)
    
    if not history_path.exists():
        print(f"Creating default agent history at {history_path}")
        history = create_default_agent_history()
        loader.save_agent_history(history)
