import os
import sys
from pathlib import Path

# Bootstrap: Add the project root (code/backend) to sys.path
root_path = str(Path(__file__).parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.agents.tutor import TutorAgent
from app.agents.evaluator import EvaluatorAgent
from app.learner_model.models import Mastery, Concept, Interaction
from app.learner_model.database import SessionLocal
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Allow CORS for the Chrome Extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tutor = TutorAgent()
evaluator = EvaluatorAgent()

class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None
    history: Optional[List[dict]] = None

class ChatResponse(BaseModel):
    reply: str
    mastery_updates: list
    mode: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # 1. Get student mastery status for mode determination
        db = SessionLocal()
        mastery_levels = db.query(Mastery).all()
        avg_score = sum([m.score for m in mastery_levels]) / len(mastery_levels) if mastery_levels else 0.5
        db.close()

        mode = "Scaffolding"
        if avg_score < 0.4: mode = "Remedial"
        elif avg_score > 0.7: mode = "Mastery"

        # 2. Get Tutor Response with context
        context_str = ""
        if request.context:
            page_text = request.context.get("text", "")[:2000]
            quizzes = "\n".join(request.context.get("quizzes", []))
            context_str = f"\n\n--- CANVAS PAGE CONTEXT ---\n{page_text}\n--- ACTIVE QUIZ QUESTIONS ---\n{quizzes}"

        reply = tutor.get_tutor_response(request.message + context_str, history=request.history)
        
        # 3. Evaluate (Wrap in try-except for robustness)
        updates = []
        try:
            updates = evaluator.evaluate_interaction(request.message, reply)
        except Exception as eval_e:
            print(f"Evaluation Error: {eval_e}")
        
        return {
            "reply": reply,
            "mastery_updates": [u.dict() for u in updates],
            "mode": mode
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mastery")
async def get_mastery():
    db = SessionLocal()
    mastery = db.query(Mastery).join(Concept).all()
    result = [{"concept": m.concept.name, "score": m.score} for m in mastery]
    db.close()
    return result

@app.get("/history")
async def get_history():
    db = SessionLocal()
    interactions = db.query(Interaction).order_by(Interaction.timestamp.desc()).limit(20).all()
    result = []
    for i in interactions:
        concept_name = db.query(Concept).filter(Concept.id == i.concept_id).first().name if i.concept_id else "General"
        result.append({
            "timestamp": i.timestamp,
            "concept": concept_name,
            "delta": i.score_delta
        })
    db.close()
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
