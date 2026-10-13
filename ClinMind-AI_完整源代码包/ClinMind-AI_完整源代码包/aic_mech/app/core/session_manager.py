"""Session Manager for ClinMind-AI Clinical Simulation.

Manages runtime state, instances of physiological engines, multi-agent engines,
action histories, and evaluation objects for concurrent or single-user sessions.
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from app.models.entities import ActionRecord, OSCEAssessment, PatientStateEnum, VitalsVector
from app.core.physiology_engine import PhysiologyEngine
from app.core.agent_engine import AgentEngine
from app.core.guardrail_engine import GuardrailEngine
from app.core.ged_evaluator import GEDEvaluator


class SimulationSession:
    """Encapsulates a single student's clinical training session."""

    def __init__(self, session_id: str, case_id: str, student_name: str = "参赛学员"):
        self.session_id: str = session_id
        self.case_id: str = case_id
        self.student_name: str = student_name
        self.start_time: float = time.time()
        self.virtual_seconds: int = 0
        self.is_active: bool = True
        self.is_finished: bool = False

        # Core Engines
        self.physiology_engine: PhysiologyEngine = PhysiologyEngine()
        self.agent_engine: AgentEngine = AgentEngine()
        self.guardrail_engine: GuardrailEngine = GuardrailEngine()
        self.ged_evaluator: GEDEvaluator = GEDEvaluator()

        # Action history and final report
        self.action_history: List[ActionRecord] = []
        self.final_assessment: Optional[OSCEAssessment] = None

    def tick(self, dt: float = 1.0) -> VitalsVector:
        """Advance session time by dt seconds."""
        if not self.is_active or self.is_finished:
            return self.physiology_engine.get_current_vitals()

        self.virtual_seconds += int(dt)
        return self.physiology_engine.advance_time(dt)


class SessionStore:
    """In-memory singleton registry for active training sessions."""

    _instance: Optional["SessionStore"] = None

    def __init__(self):
        self._sessions: Dict[str, SimulationSession] = {}
        self._default_session_id: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "SessionStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_session(self, case_id: str, student_name: str = "参赛学员") -> SimulationSession:
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        session = SimulationSession(session_id, case_id, student_name)
        self._sessions[session_id] = session
        self._default_session_id = session_id
        return session

    def get_session(self, session_id: Optional[str] = None) -> Optional[SimulationSession]:
        if not session_id or session_id == "default":
            session_id = self._default_session_id

        if session_id and session_id in self._sessions:
            return self._sessions[session_id]

        # If no session exists yet, auto-create one for seamless standalone run
        if not self._sessions:
            return self.create_session("case_chest_pain_001", "参赛学员")

        return next(iter(self._sessions.values()), None)

    def get_all_sessions(self) -> Dict[str, SimulationSession]:
        return self._sessions
