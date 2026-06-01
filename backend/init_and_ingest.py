import os
from app.learner_model.database import init_db
from app.ingestion.processor import IngestionProcessor
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    # Check if OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in .env file.")
        return

    print("Initializing Database...")
    init_db()
    
    print("Starting Ingestion...")
    processor = IngestionProcessor()
    raw_file = "code/data/raw/linear_regression.txt"
    
    if os.path.exists(raw_file):
        processor.process_and_index(raw_file)
        print(f"Successfully indexed {raw_file} and extracted concepts.")
    else:
        print(f"File not found: {raw_file}")

if __name__ == "__main__":
    main()
