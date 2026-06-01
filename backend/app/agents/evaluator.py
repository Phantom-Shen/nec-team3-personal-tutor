from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
import os
from langchain_core.prompts import ChatPromptTemplate
from ..learner_model.models import Concept, Mastery, Interaction
from ..learner_model.database import SessionLocal
import datetime

class ConceptUpdate(BaseModel):
    concept_name: str = Field(description="Name of the concept being evaluated")
    score_delta: float = Field(description="Adjustment to mastery score, between -0.2 and 0.2")
    reason: str = Field(description="Brief reason for the adjustment")

class EvaluationResult(BaseModel):
    updates: List[ConceptUpdate]

class EvaluatorAgent:
    def __init__(self, model_name: Optional[str] = None):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "your_key_here":
            self.llm = ChatOpenAI(model=model_name or "gpt-4o-mini", temperature=0)
        else:
            local_model = os.getenv("LOCAL_MODEL_NAME", "gemma3:1b")
            self.llm = ChatOllama(model=local_model, temperature=0)

    def evaluate_interaction(self, student_input: str, tutor_response: str):
        db = SessionLocal()
        concepts = db.query(Concept).all()
        concept_list_str = "\n".join([f"- {c.name}: {c.description}" for c in concepts])
        
        prompt = ChatPromptTemplate.from_template(
            "You are an educational evaluator. Analyze the student's interaction with the tutor. "
            "Identify which of the following concepts the student is demonstrating knowledge of (or lack thereof). "
            "Assign a score delta (-0.2 to 0.2) based on their understanding. "
            "A question might indicate a lack of understanding (negative delta) or a sophisticated grasp (positive delta). "
            "\n\nAvailable Concepts:\n{concept_list}\n\n"
            "Interaction:\nStudent: {student_input}\nTutor: {tutor_response}"
        )
        
        chain = prompt | self.llm.with_structured_output(EvaluationResult)
        result = chain.invoke({
            "concept_list": concept_list_str,
            "student_input": student_input,
            "tutor_response": tutor_response
        })

        for update in result.updates:
            concept = db.query(Concept).filter(Concept.name == update.concept_name).first()
            if concept:
                mastery = db.query(Mastery).filter(Mastery.concept_id == concept.id).first()
                if mastery:
                    # Update score and clamp between 0 and 1
                    mastery.score = max(0.0, min(1.0, mastery.score + update.score_delta))
                    mastery.last_updated = datetime.datetime.utcnow()
                
                # Log interaction
                interaction = Interaction(
                    interaction_type="evaluation",
                    content=f"Delta: {update.score_delta}, Reason: {update.reason}",
                    concept_id=concept.id,
                    score_delta=update.score_delta
                )
                db.add(interaction)
        
        db.commit()
        db.close()
        return result.updates
