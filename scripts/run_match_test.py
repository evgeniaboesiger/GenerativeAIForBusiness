from app.matching.engine import score_candidate_job
import json
candidate = {
    'id': 1,
    'skills': [{'skill':'Python','level':'expert'},{'skill':'SQL','level':'advanced'},{'skill':'Excel','level':'advanced'}],
    'years_experience':4,
    'education':[{'degree':'MSc','field':'Data Science'}],
    'languages':[{'language':'German','level':'B2'},{'language':'English','level':'C1'}],
    'salary_expectation_min':80000,'salary_expectation_max':95000,
    'employment_percentage_min':80,'employment_percentage_max':100,'location':'Zurich','maximum_commute_minutes':60,'remote_preference':'hybrid',
}
job = {
    'id': 10,
    'title':'Data Analyst',
    'company':'Alpine Digital AG',
    'location':'Zurich',
    'required_skills':[{'skill':'Python','mandatory':True},{'skill':'SQL','mandatory':True}],
    'preferred_skills':['Power BI'],
    'minimum_years_experience':3,
    'education_requirements':'MSc',
    'language_requirements':[{'language':'German','level':'B2','mandatory':True}],
    'salary_min':75000,'salary_max':95000,'remote_percentage':50
}
res = score_candidate_job(candidate, job)
print(json.dumps(res, indent=2))
