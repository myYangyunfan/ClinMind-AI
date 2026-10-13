"""Case Management and Session Initialization REST Routes."""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import StartCaseRequest, CaseSummaryDTO, SessionStateResponse
from app.core.session_manager import SessionStore
import config
import json

router = APIRouter(prefix="/api/case", tags=["Case Management"])


@router.get("/list", response_model=List[CaseSummaryDTO])
async def list_cases():
    """Return all available clinical competition cases."""
    case_path = config.DATA_DIR / "case_chest_pain.json"
    if not case_path.exists():
        raise HTTPException(status_code=404, detail="Case repository not found")

    with open(case_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [
        CaseSummaryDTO(
            case_id=data.get("case_id", "case_chest_pain_001"),
            title=data.get("title", ""),
            difficulty=data.get("difficulty", "国家级学科竞赛 (Hard)"),
            chief_complaint=data.get("chief_complaint", ""),
            target_competency="急性高危胸痛鉴别诊断、血流动力学紧急调控、抗栓禁忌识别、CTA确诊路径",
            description="52岁男性企业高管，突发剧烈撕裂样胸背痛3小时伴大汗。考验学员在STEMI与主动脉夹层之间的生死鉴别与决断。"
        )
    ]


@router.get("/detail/{case_id}")
async def get_case_detail(case_id: str):
    """Get full case briefing and patient profile."""
    case_path = config.DATA_DIR / "case_chest_pain.json"
    if not case_path.exists():
        raise HTTPException(status_code=404, detail="Case not found")

    with open(case_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "case_id": data.get("case_id"),
        "title": data.get("title"),
        "chief_complaint": data.get("chief_complaint"),
        "patient_profile": data.get("patient_profile"),
        "initial_vitals": data.get("initial_vitals")
    }


@router.post("/start")
async def start_case(req: StartCaseRequest):
    """Initialize or reset an active simulation training session."""
    store = SessionStore.get_instance()
    session = store.create_session(req.case_id, req.student_name)

    return {
        "status": "success",
        "message": "抢救室实训已就绪，患者已接入多参数心电监护仪，计时开始！",
        "session_id": session.session_id,
        "case_id": session.case_id,
        "student_name": session.student_name,
        "initial_vitals": session.physiology_engine.get_current_vitals(),
        "patient_state": session.physiology_engine.get_state().value
    }


@router.get("/session/status", response_model=SessionStateResponse)
async def get_session_status(session_id: str = Query(default="default")):
    """Get active training session snapshot."""
    store = SessionStore.get_instance()
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Active session not found")

    vitals = session.physiology_engine.get_current_vitals()
    state = session.physiology_engine.get_state()

    return SessionStateResponse(
        session_id=session.session_id,
        case_id=session.case_id,
        student_name=session.student_name,
        is_active=session.is_active,
        elapsed_virtual_seconds=session.virtual_seconds,
        patient_state=state,
        vitals=vitals,
        agent_trust=round(session.agent_engine.state.patient_trust, 2),
        agent_anxiety=round(session.agent_engine.state.family_anxiety, 2),
        history_actions_count=len(session.action_history),
        active_alarms=session.agent_engine.state.active_critical_alarms
    )
