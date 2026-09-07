"""
Seed script for FRAUMATCH demo data.
Deterministic random seed used for reproducibility.
"""
import random
import sys
from datetime import date
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models import (
    AIRun,
    Assessment,
    Candidate,
    Education,
    Experience,
    Job,
    Skill,
)


def create_engine_and_session():
    engine = create_engine(settings.database_url, future=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, Session


FIRST_NAMES = [
    "Anna", "Sofia", "Elena", "Maria", "Laura", "Nina", "Julia", "Sara", "Emma", "Clara",
    "Lena", "Maya", "Isabella", "Valentina", "Lea", "Ariane", "Noemi", "Patricia", "Simone", "Carla",
]

LAST_NAMES = [
    "Müller", "Rossi", "Schneider", "Meier", "Keller", "Weber", "Baumann", "Fischer", "Frei", "Zimmermann",
    "Lindt", "Graf", "Huber", "Brunner", "Schmid", "Kunz", "Hofmann", "Bachmann", "Linden", "Gonzalez",
]

SWISS_LOCATIONS = [
    "Zurich", "Winterthur", "Baden", "Zug", "Bern", "Basel", "Lausanne", "Geneva", "Lucerne", "St. Gallen",
    "Aarau", "Dielsdorf", "Uster", "Dietikon", "Schlieren", "Bülach",
]

SKILLS_LIBRARY = [
    "Python", "SQL", "JavaScript", "TypeScript", "React", "Java", "C#", "Excel", "Power BI", "Tableau",
    "R", "Data Analysis", "Machine Learning", "Project Management", "Agile", "Scrum", "Jira", "HubSpot",
    "Salesforce", "Google Analytics", "SEO", "SEM", "Content Marketing", "Social Media", "Canva",
    "Adobe Creative Suite", "UX Research", "UI Design", "Figma", "Recruitment", "HR Administration",
    "Payroll", "Accounting", "Financial Analysis", "Business Development", "Sales", "Account Management",
    "Customer Success", "Communication", "Presentation", "Market Research", "CRM", "Operations",
    "Supply Chain", "Negotiation", "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Linux",
    "Network Security", "Unit Testing",
]


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def seed():
    random.seed(42)
    _engine, Session = create_engine_and_session()
    session = Session()

    session.query(AIRun).delete()
    session.query(Assessment).delete()
    session.query(Job).delete()
    session.query(Education).delete()
    session.query(Experience).delete()
    session.query(Skill).delete()
    session.query(Candidate).delete()
    session.commit()

    companies = [
        "Alpine Digital AG", "Helvetia Analytics AG", "Zurich GreenTech GmbH", "NovaCare Solutions AG",
        "SwissBridge Consulting AG", "Limmat Finance AG", "AlpData Systems AG", "Rhein Talent Solutions AG",
        "Urban Mobility Switzerland AG", "Helvetic Cloud AG",
    ]

    jobs = []
    for _ in range(50):
        company = random.choice(companies)
        title = random.choice([
            "Software Developer", "Data Analyst", "Digital Marketing Specialist", "HR Specialist",
            "Project Coordinator", "Financial Analyst", "Account Manager", "UX/UI Designer",
            "Business Consultant", "Operations Specialist",
        ])
        location = random.choice(SWISS_LOCATIONS)
        salary_min = random.randint(65000, 110000)
        salary_max = salary_min + random.randint(10000, 40000)
        required_skills = random.sample(SKILLS_LIBRARY, k=random.randint(3, 6))
        preferred_skills = random.sample([s for s in SKILLS_LIBRARY if s not in required_skills], k=random.randint(1, 4))

        job = Job(
            company=company,
            title=title,
            location=location,
            employment_percentage=random.choice([50, 60, 80, 100]),
            salary_min=salary_min,
            salary_max=salary_max,
            description=f"Synthetic role: {title} at {company}",
            requirements="",
            required_skills=[{"skill": skill, "mandatory": True} for skill in required_skills],
            preferred_skills=preferred_skills,
            language_requirements=[{"language": "German", "level": "B2", "mandatory": True}],
            minimum_years_experience=random.choice([0, 1, 2, 3, 5]),
            education_requirements=random.choice(["Bachelor", "Master", None]),
            required_certifications=None,
            nice_to_have_certifications=None,
        )
        session.add(job)
        jobs.append(job)

    session.commit()

    candidates = []
    for i in range(100):
        location = random.choice(SWISS_LOCATIONS)
        salary_min = random.randint(50000, 90000)
        salary_max = salary_min + random.randint(5000, 40000)
        remote_pref = random.choice(["office", "hybrid", "remote"])
        career_goal = random.choice([
            "Senior Software Engineer", "Data Analyst", "Project Manager", "Marketing Specialist",
            "HR Specialist", "Business Analyst",
        ])

        candidate = Candidate(
            name=random_name(),
            email=f"demo{i}@example.local",
            location=location,
            employment_percentage=random.choice([50, 60, 80, 100]),
            salary_min=salary_min,
            salary_max=salary_max,
            remote_preference=remote_pref,
            career_goal=career_goal,
        )
        session.add(candidate)
        candidates.append(candidate)

    session.commit()

    for idx, candidate in enumerate(candidates):
        edu = Education(
            candidate_id=candidate.id,
            institution=random.choice([
                "University of Applied Sciences Zurich",
                "European Business School",
                "International Institute of Technology",
            ]),
            degree=random.choice(["Bachelor", "Master", "MBA"]),
            field=random.choice(["Computer Science", "Business", "Economics", "Marketing", "Data Science"]),
            year=random.randint(2008, 2022),
            verified=random.choice([True, False]),
        )
        session.add(edu)

        for _ in range(random.randint(1, 4)):
            start_year = random.randint(2008, 2019)
            end_year = random.choice([start_year + 1, start_year + 2, start_year + 3, None])
            session.add(
                Experience(
                    candidate_id=candidate.id,
                    company=random.choice(companies),
                    job_title=random.choice(["Coordinator", "Specialist", "Engineer", "Analyst", "Manager"]),
                    start_date=date(start_year, 1, 1),
                    end_date=date(end_year, 1, 1) if end_year else None,
                    description="Synthetic experience",
                    verified=random.choice([True, False]),
                    source=random.choice(["cv", "linkedin"]),
                )
            )

        for skill in random.sample(SKILLS_LIBRARY, k=random.randint(5, 12)):
            session.add(
                Skill(
                    candidate_id=candidate.id,
                    skill=skill,
                    level=random.choice(["beginner", "intermediate", "advanced", "expert"]),
                    verified=random.choice([True, False]),
                    source=random.choice(["cv", "certificate", "reference"]),
                )
            )

        if idx % 3 == 0:
            session.add(
                Assessment(
                    candidate_id=candidate.id,
                    job_id=random.choice(jobs).id,
                    type=random.choice(["technical", "language", "numerical_reasoning", "situational_judgement"]),
                    score=random.randint(50, 98),
                    result="completed",
                )
            )

    session.commit()
    print(f"Seeding complete: {len(candidates)} candidates and {len(jobs)} jobs")
    return {"candidates": len(candidates), "jobs": len(jobs)}


if __name__ == "__main__":
    seed()
