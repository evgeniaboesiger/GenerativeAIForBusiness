import sys, json
sys.path.append('agents')
from profile_agent import ProfileAgent

agent = ProfileAgent()

with open('data/sample_cvs.json', encoding='utf-8') as f:
    cvs = json.load(f)

cv = cvs[0]['cv_text']
print("Extracting profile for:", cvs[0]['name'])
print("(This may take 20-60 seconds on first run)...")
result = agent.extract_profile(cv)
print(json.dumps(result, indent=2)[:1500])
