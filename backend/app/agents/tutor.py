from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from ..learner_model.models import Concept, Mastery
from ..learner_model.database import SessionLocal
import os
from typing import Optional, List

class TutorAgent:
    def __init__(self, model_name: Optional[str] = None):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "your_key_here":
            self.llm = ChatOpenAI(model=model_name or "gpt-4o-mini", temperature=0.7)
            self.embeddings = OpenAIEmbeddings()
        else:
            local_model = os.getenv("LOCAL_MODEL_NAME", "gemma3:1b")
            embed_model = os.getenv("LOCAL_EMBEDDING_MODEL", "nomic-embed-text")
            self.llm = ChatOllama(model=local_model, temperature=0.0)
            self.embeddings = OllamaEmbeddings(model=embed_model)
            
        self.vector_db_path = "code/data/processed/chroma_db"
        self.vectorstore = Chroma(
            persist_directory=self.vector_db_path, 
            embedding_function=self.embeddings
        )

    def get_tutor_response(self, student_input: str, history: Optional[List[dict]] = None):
        # 1. Retrieve context (Try RAG, fallback to simple keyword match if embeddings fail)
        try:
            docs = self.vectorstore.similarity_search(student_input, k=3)
            context = "\n".join([doc.page_content for doc in docs])
        except Exception:
            # Fallback: Simple keyword match in the raw text file
            context = "No specific context found. Use general knowledge about Linear Regression (y=mx+b, MSE, Gradient Descent)."
            try:
                raw_path = "code/data/raw/linear_regression.txt"
                if os.path.exists(raw_path):
                    with open(raw_path, 'r') as f:
                        text = f.read()
                        # Very simple heuristic: find sentences containing words from the input
                        keywords = [w.lower() for w in student_input.split() if len(w) > 3]
                        lines = text.split('\n')
                        matches = [l for l in lines if any(k in l.lower() for k in keywords)]
                        if matches:
                            context = "\n".join(matches[:5])
            except Exception:
                pass

        # 2. Get student mastery status
        db = SessionLocal()
        # For simplicity, we get the average mastery of all concepts or identify relevant ones
        # Real version would identify concepts from the RAG context first
        mastery_levels = db.query(Mastery).all()
        avg_score = sum([m.score for m in mastery_levels]) / len(mastery_levels) if mastery_levels else 0.5
        db.close()

        # 3. Choose Persona based on score
        base_instruction = (
            "YOU ARE A HELPFUL AI TUTOR. ADAPT YOUR BEHAVIOR BASED ON INTENT:\n"
            "1. TASK/ASSIGNMENT ASSISTANCE: If the student asks to write something (titles, drafts, sections), NEVER do the work for them. "
            "Instead, act as a Socratic guide: provide a strategy and ask a guiding question to help them start.\n"
            "2. CONCEPTUAL/GENERAL QUESTIONS: If the student asks to understand a concept or asks a general question, explain it clearly and concisely, "
            "then ask a follow-up question to check their understanding.\n"
            "3. GREETINGS: Respond naturally and politely.\n"
            "STRIKE RULES: Never write paper sections/titles. Never use placeholders like [Name]. Stay brief."
        )

        if avg_score < 0.4:
            persona = f"{base_instruction}\nPersona: Patient Remedial Tutor. Use very simple words."
        elif avg_score > 0.7:
            persona = f"{base_instruction}\nPersona: Challenging Mentor. Be very critical and brief."
        else:
            persona = f"{base_instruction}\nPersona: Scaffolding Tutor. Focus on concepts."

        prompt_messages = [("system", "{persona}")]
        
        # Add history to the prompt if available
        if history:
            # Only keep the last 5 turns to stay within context limits of small models
            for msg in history[-10:]: 
                role = "human" if msg["sender"] == "user" else "ai"
                prompt_messages.append((role, msg["text"]))

        prompt_messages.append(("human", "Course Context:\n{context}\n\nStudent Question: {student_input}"))

        prompt = ChatPromptTemplate.from_messages(prompt_messages)
        
        chain = prompt | self.llm
        response = chain.invoke({
            "persona": persona,
            "context": context,
            "student_input": student_input
        })

        return response.content
