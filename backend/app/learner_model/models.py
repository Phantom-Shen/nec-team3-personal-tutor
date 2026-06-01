from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
import datetime

Base = declarative_base()

class Concept(Base):
    __tablename__ = "concepts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    
    mastery = relationship("Mastery", back_populates="concept", uselist=False)

class Mastery(Base):
    __tablename__ = "mastery"
    id = Column(Integer, primary_key=True, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id"))
    score = Column(Float, default=0.0)  # 0.0 to 1.0
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)
    
    concept = relationship("Concept", back_populates="mastery")

class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    interaction_type = Column(String)  # 'question', 'answer', 'quiz_pass', 'quiz_fail'
    content = Column(String)
    concept_id = Column(Integer, ForeignKey("concepts.id"), nullable=True)
    score_delta = Column(Float, default=0.0)
