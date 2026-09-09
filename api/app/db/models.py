from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    Date,
    Float,
    Numeric,
    JSON as JSONType,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class Candidate(Base):
    __tablename__ = 'candidates'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    location = Column(String)
    employment_percentage = Column(Integer)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    remote_preference = Column(String)
    career_goal = Column(Text)
    personality = Column(JSONType)
    values = Column(JSONType)
    preference_tiers = Column(JSONType)
    created_at = Column(DateTime, default=datetime.utcnow)

    experiences = relationship('Experience', back_populates='candidate', cascade='all, delete')
    skills = relationship('Skill', back_populates='candidate', cascade='all, delete')
    education = relationship('Education', back_populates='candidate', cascade='all, delete')


class ProfileExtraction(Base):
    __tablename__ = 'profile_extractions'
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=True)
    source = Column(String, default='cv')
    raw_text = Column(Text)
    profile_json = Column(JSONType)
    model_name = Column(String)
    execution_time_ms = Column(Integer)
    token_estimate = Column(Integer)
    estimated_cost = Column(Numeric(10, 6))
    created_at = Column(DateTime, default=datetime.utcnow)


class ProfileReview(Base):
    __tablename__ = 'profile_reviews'
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)
    profile_json = Column(JSONType)
    review_status = Column(String, default='candidate_confirmed')
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Experience(Base):
    __tablename__ = 'experience'
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'))
    company = Column(String)
    job_title = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    description = Column(Text)
    verified = Column(Boolean, default=False)
    source = Column(String)

    candidate = relationship('Candidate', back_populates='experiences')


class Skill(Base):
    __tablename__ = 'skills'
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'))
    skill = Column(String, nullable=False)
    level = Column(String)
    verified = Column(Boolean, default=False)
    source = Column(String)

    candidate = relationship('Candidate', back_populates='skills')


class Education(Base):
    __tablename__ = 'education'
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'))
    institution = Column(String)
    degree = Column(String)
    field = Column(String)
    year = Column(Integer)
    verified = Column(Boolean, default=False)

    candidate = relationship('Candidate', back_populates='education')


class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True, index=True)
    company = Column(String)
    title = Column(String, nullable=False)
    location = Column(String)
    employment_percentage = Column(Integer)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    description = Column(Text)
    requirements = Column(Text)
    required_skills = Column(JSONType)
    preferred_skills = Column(JSONType)
    language_requirements = Column(JSONType)
    created_at = Column(DateTime, default=datetime.utcnow)
    minimum_years_experience = Column(Integer)
    education_requirements = Column(Text)
    required_certifications = Column(JSONType)
    nice_to_have_certifications = Column(JSONType)
    company_values = Column(JSONType)
    personality_preferences = Column(JSONType)


class Match(Base):
    __tablename__ = 'matches'
    candidate_id = Column(Integer, ForeignKey('candidates.id'), primary_key=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), primary_key=True)
    skills_score = Column(Float)
    experience_score = Column(Float)
    education_score = Column(Float)
    language_score = Column(Float)
    location_score = Column(Float)
    preference_score = Column(Float)
    overall_score = Column(Float)
    explanation = Column(Text)


class MatchingLog(Base):
    __tablename__ = 'matching_logs'
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'))
    job_id = Column(Integer, ForeignKey('jobs.id'))
    execution_time_ms = Column(Integer)
    algorithm_version = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Workflow(Base):
    __tablename__ = 'workflows'
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String, unique=True, index=True, nullable=False)
    candidate_id = Column(Integer, ForeignKey('candidates.id'))
    job_id = Column(Integer, ForeignKey('jobs.id'))
    state = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class AgentLog(Base):
    __tablename__ = 'agent_logs'
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String)
    agent = Column(String)
    agent_version = Column(String)
    status = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    latency_ms = Column(Integer)
    model = Column(String)
    estimated_cost = Column(Numeric(10,6))
    input_reference = Column(JSONType)
    output_reference = Column(JSONType)
    error = Column(Text)


class Application(Base):
    __tablename__ = 'applications'
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'))
    job_id = Column(Integer, ForeignKey('jobs.id'))
    cv = Column(Text)
    cover_letter = Column(Text)
    status = Column(String, default='submitted')
    created_at = Column(DateTime, default=datetime.utcnow)


class Assessment(Base):
    __tablename__ = 'assessments'
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'))
    job_id = Column(Integer, ForeignKey('jobs.id'))
    type = Column(String)
    score = Column(Float)
    result = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Verification(Base):
    __tablename__ = 'verification'
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'))
    document = Column(Text)
    status = Column(String)
    verification_source = Column(String)
    confidence = Column(Numeric(5,4))
    created_at = Column(DateTime, default=datetime.utcnow)


class AIRun(Base):
    __tablename__ = 'ai_runs'
    id = Column(Integer, primary_key=True, index=True)
    agent = Column(String)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    latency_ms = Column(Integer)
    estimated_cost = Column(Numeric(10,6))
    model = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
