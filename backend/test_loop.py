from app.agents.tutor import TutorAgent
from app.agents.evaluator import EvaluatorAgent
from app.learner_model.database import SessionLocal
from app.learner_model.models import Mastery, Concept
from dotenv import load_dotenv

def print_mastery():
    db = SessionLocal()
    mastery = db.query(Mastery).join(Concept).all()
    print("\n--- Current Mastery Status ---")
    for m in mastery:
        print(f"Concept: {m.concept.name} | Score: {m.score:.2f}")
    print("------------------------------\n")
    db.close()

def main():
    load_dotenv()
    tutor = TutorAgent()
    evaluator = EvaluatorAgent()
    
    print("Welcome to your Personal AI Tutor!")
    print_mastery()
    
    while True:
        student_input = input("You: ")
        if student_input.lower() in ["exit", "quit"]:
            break
            
        # 1. Get Tutor Response
        response = tutor.get_tutor_response(student_input)
        print(f"\nTutor: {response}\n")
        
        # 2. Evaluate Interaction
        print("(System: Evaluating your understanding...)")
        updates = evaluator.evaluate_interaction(student_input, response)
        
        # 3. Show Mastery Updates
        print_mastery()

if __name__ == "__main__":
    main()
