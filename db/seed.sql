-- Seed data for FRAUMATCH

-- Candidates
INSERT INTO candidates (name, email, location, employment_percentage, salary_min, salary_max, remote_preference, career_goal)
VALUES
('Anna Müller','anna.mueller@example.ch','Zürich',80,70000,90000,'hybrid','Senior project manager role'),
('Maria Schneider','maria.schneider@example.ch','Bern',100,90000,120000,'office','Backend developer');

-- Experiences
INSERT INTO experience (candidate_id, company, job_title, start_date, end_date, description, verified, source)
VALUES
(1, 'SwissTech GmbH', 'Projektleiterin', '2018-05-01', '2023-06-30', 'Managed EU-funded projects', true, 'linkedin'),
(2, 'Innovatech AG', 'Software Engineer', '2019-01-01', NULL, 'Backend services in Python', false, 'cv');

-- Skills
INSERT INTO skills (candidate_id, skill, level, verified, source)
VALUES
(1, 'Project Management', 'senior', true, 'reference'),
(1, 'Agile', 'advanced', false, 'cv'),
(2, 'Python', 'senior', true, 'certificate');

-- Education
INSERT INTO education (candidate_id, institution, degree, field, year, verified)
VALUES
(1, 'University of Zurich', 'MSc', 'Management', 2017, true),
(2, 'ETH Zurich', 'BSc', 'Computer Science', 2018, false);

-- Jobs
INSERT INTO jobs (company, title, location, employment_percentage, salary_min, salary_max, description, requirements, required_skills, preferred_skills, language_requirements)
VALUES
('SwissTech GmbH','Projektmanagerin','Zürich',80,70000,90000,'Project management role for public sector','PMP or equivalent','["Project Management"]'::jsonb,'["German"]'::jsonb,'["German","English"]'::jsonb),
('Innovatech AG','Senior Backend Engineer','Bern',100,100000,140000,'Backend engineer for scalable services','5+ yrs backend','["Python","Postgres"]'::jsonb,'["Docker"]'::jsonb,'["English"]'::jsonb);

-- Example AI run audit
INSERT INTO ai_runs (agent, input_tokens, output_tokens, latency_ms, estimated_cost, model)
VALUES ('match-scoring-service', 120, 430, 250, 0.0123, 'gpt-4o-mini');

