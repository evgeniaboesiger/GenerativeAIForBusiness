-- FRAUMATCH schema for PostgreSQL

-- Candidates
CREATE TABLE candidates (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  location TEXT,
  employment_percentage INTEGER,
  salary_min INTEGER,
  salary_max INTEGER,
  remote_preference TEXT,
  career_goal TEXT,
  personality JSONB,
  values JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Experience items for candidates
CREATE TABLE experience (
  id SERIAL PRIMARY KEY,
  candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  company TEXT,
  job_title TEXT,
  start_date DATE,
  end_date DATE,
  description TEXT,
  verified BOOLEAN DEFAULT FALSE,
  source TEXT
);

-- Skills for candidates
CREATE TABLE skills (
  id SERIAL PRIMARY KEY,
  candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  skill TEXT NOT NULL,
  level TEXT,
  verified BOOLEAN DEFAULT FALSE,
  source TEXT
);

-- Education
CREATE TABLE education (
  id SERIAL PRIMARY KEY,
  candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  institution TEXT,
  degree TEXT,
  field TEXT,
  year INTEGER,
  verified BOOLEAN DEFAULT FALSE
);

-- Jobs table
CREATE TABLE jobs (
  id SERIAL PRIMARY KEY,
  company TEXT,
  title TEXT NOT NULL,
  location TEXT,
  employment_percentage INTEGER,
  salary_min INTEGER,
  salary_max INTEGER,
  description TEXT,
  requirements TEXT,
  required_skills JSONB,
  preferred_skills JSONB,
  language_requirements JSONB,
  minimum_years_experience INTEGER,
  education_requirements TEXT,
  required_certifications JSONB,
  nice_to_have_certifications JSONB,
  company_values JSONB,
  personality_preferences JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Matches (candidate-job scoring)
CREATE TABLE matches (
  candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  skills_score REAL,
  experience_score REAL,
  education_score REAL,
  language_score REAL,
  location_score REAL,
  preference_score REAL,
  overall_score REAL,
  explanation TEXT,
  PRIMARY KEY (candidate_id, job_id)
);

-- Matching performance logs
CREATE TABLE matching_logs (
  id SERIAL PRIMARY KEY,
  candidate_id INTEGER REFERENCES candidates(id),
  job_id INTEGER REFERENCES jobs(id),
  execution_time_ms INTEGER,
  algorithm_version TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Workflow orchestration tables
CREATE TABLE workflows (
  id SERIAL PRIMARY KEY,
  workflow_id TEXT UNIQUE NOT NULL,
  candidate_id INTEGER REFERENCES candidates(id),
  job_id INTEGER REFERENCES jobs(id),
  state TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE agent_logs (
  id SERIAL PRIMARY KEY,
  workflow_id TEXT,
  agent TEXT,
  agent_version TEXT,
  status TEXT,
  start_time TIMESTAMP WITH TIME ZONE,
  end_time TIMESTAMP WITH TIME ZONE,
  latency_ms INTEGER,
  model TEXT,
  estimated_cost NUMERIC(10,6),
  input_reference JSONB,
  output_reference JSONB,
  error TEXT
);

CREATE TABLE profile_extractions (
  id SERIAL PRIMARY KEY,
  candidate_id INTEGER REFERENCES candidates(id),
  source TEXT,
  raw_text TEXT,
  profile_json JSONB,
  model_name TEXT,
  execution_time_ms INTEGER,
  token_estimate INTEGER,
  estimated_cost NUMERIC(10,6),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE profile_reviews (
  id SERIAL PRIMARY KEY,
  candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  profile_json JSONB,
  review_status TEXT DEFAULT 'candidate_confirmed',
  notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Applications
CREATE TABLE applications (
  id SERIAL PRIMARY KEY,
  candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  cv TEXT,
  cover_letter TEXT,
  status TEXT DEFAULT 'submitted',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Assessments
CREATE TABLE assessments (
  id SERIAL PRIMARY KEY,
  candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  type TEXT,
  score REAL,
  result TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Verification records
CREATE TABLE verification (
  id SERIAL PRIMARY KEY,
  candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  document TEXT,
  status TEXT,
  verification_source TEXT,
  confidence REAL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- AI runs audit
CREATE TABLE ai_runs (
  id SERIAL PRIMARY KEY,
  agent TEXT,
  input_tokens INTEGER,
  output_tokens INTEGER,
  latency_ms INTEGER,
  estimated_cost NUMERIC(10,6),
  model TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
