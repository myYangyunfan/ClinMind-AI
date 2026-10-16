"""OSCE Clinical Reasoning Assessment and GED Evaluation REST Routes."""

import asyncio
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import EvaluationRequest, EvaluationResponse
from app.core.session_manager import SessionStore
import json
import config

router = APIRouter(prefix="/api/eval", tags=["Clinical Assessment & Evaluation"])


@router.post("/submit", response_model=EvaluationResponse)
async def submit_case_evaluation(req: EvaluationRequest):
    """Finalize clinical case, trigger GED topological evaluation, and return OSCE radar report."""
    store = SessionStore.get_instance()
    session = store.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Mark session as closed
    session.is_finished = True
    session.is_active = False

    # Execute NetworkX Graph Edit Distance evaluation. The evaluator may call
    # the synchronous LLM client when online, so keep it off the event loop.
    assessment = await asyncio.to_thread(
        session.ged_evaluator.evaluate,
        session.action_history,
        req.final_diagnosis
    )
    session.final_assessment = assessment

    return EvaluationResponse(
        session_id=session.session_id,
        student_name=session.student_name,
        total_score=assessment.total_score,
        ged_distance=assessment.ged_distance,
        topological_similarity=assessment.topological_similarity,
        radar_scores=assessment.radar_scores,
        fatal_errors=assessment.fatal_errors,
        clinical_feedback=assessment.clinical_feedback,
        action_sequence_summary=assessment.action_sequence_summary,
        comparison_dag=assessment.comparison_dag
    )


@router.get("/report/{session_id}", response_model=EvaluationResponse)
async def get_evaluation_report(session_id: str):
    """Retrieve existing evaluation report for session."""
    store = SessionStore.get_instance()
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.final_assessment:
        # If not evaluated yet, generate on-the-fly
        assessment = await asyncio.to_thread(
            session.ged_evaluator.evaluate, session.action_history, ""
        )
        session.final_assessment = assessment

    assessment = session.final_assessment
    return EvaluationResponse(
        session_id=session.session_id,
        student_name=session.student_name,
        total_score=assessment.total_score,
        ged_distance=assessment.ged_distance,
        topological_similarity=assessment.topological_similarity,
        radar_scores=assessment.radar_scores,
        fatal_errors=assessment.fatal_errors,
        clinical_feedback=assessment.clinical_feedback,
        action_sequence_summary=assessment.action_sequence_summary,
        comparison_dag=assessment.comparison_dag
    )


@router.get("/golden_dag")
async def get_expert_golden_dag():
    """Retrieve the raw 18-node, 22-edge Expert Golden Standard DAG definition."""
    path = config.DATA_DIR / "expert_golden_dag.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Golden DAG file not found")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
