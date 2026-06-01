import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..learner_model.models import Concept, Mastery
from ..learner_model.database import SessionLocal

class ConceptExtraction(BaseModel):
    name: str = Field(description="Name of the concept")
    description: str = Field(description="Short description of what the concept covers")

class ConceptList(BaseModel):
    concepts: List[ConceptExtraction]

class IngestionProcessor:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.embeddings = OpenAIEmbeddings()
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        self.vector_db_path = "code/data/processed/chroma_db"

    def load_document(self, file_path: str):
        if file_path.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith(".docx"):
            loader = Docx2txtLoader(file_path)
        else:
            loader = TextLoader(file_path)
        return loader.load()

    def extract_concepts(self, text: str) -> List[ConceptExtraction]:
        prompt = ChatPromptTemplate.from_template(
            "Extract the key educational concepts from the following course material. "
            "For each concept, provide a name and a brief description. "
            "Material:\n\n{text}"
        )
        chain = prompt | self.llm.with_structured_output(ConceptList)
        # We only use a portion of the text to extract high-level concepts to save tokens
        result = chain.invoke({"text": text[:10000]}) 
        return result.concepts

    def process_and_index(self, file_path: str):
        # 1. Load and Split
        docs = self.load_document(file_path)
        splits = self.text_splitter.split_documents(docs)
        
        # 2. Extract Concepts (using full text content)
        full_text = "\n".join([doc.page_content for doc in docs])
        extracted_concepts = self.extract_concepts(full_text)
        
        # 3. Store in SQLite
        db = SessionLocal()
        for c in extracted_concepts:
            # Check if concept already exists
            existing = db.query(Concept).filter(Concept.name == c.name).first()
            if not existing:
                new_concept = Concept(name=c.name, description=c.description)
                db.add(new_concept)
                db.flush() # Get the ID
                new_mastery = Mastery(concept_id=new_concept.id, score=0.0)
                db.add(new_mastery)
        db.commit()
        db.close()

        # 4. Store in ChromaDB (Wrap in try-except so concept extraction still works)
        try:
            vectorstore = Chroma.from_documents(
                documents=splits,
                embedding=self.embeddings,
                persist_directory=self.vector_db_path
            )
            return vectorstore
        except Exception as e:
            print(f"Warning: Vector storage failed (Embeddings not supported). Fallback to keyword search will be used. Error: {e}")
            return None
