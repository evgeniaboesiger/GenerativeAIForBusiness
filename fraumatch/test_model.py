import sys, json, time
sys.path.append('agents')
from profile_agent import ProfileAgent

agent = ProfileAgent()  # llama3.2 (3b)

with open('data/sample_cvs.json', encoding='utf-8') as f:
    cvs = json.load(f)

prompt = agent._create_extraction_prompt(cvs[0]['cv_text'])

# Call 1
t0 = time.time()
resp1 = agent._call_ollama(prompt)
t1 = time.time()
print(f'Call 1 (3b): {t1-t0:.1f}s, len={len(resp1)}, error={"error" in resp1}')

# Call 2 - model should be cached now
t0 = time.time()
resp2 = agent._call_ollama(prompt)
t1 = time.time()
print(f'Call 2 (3b): {t1-t0:.1f}s, len={len(resp2)}, error={"error" in resp2}')

if 'error' not in resp2:
    p = agent._parse_response(resp2)
    print('Parsed OK:', 'error' not in p)
    if 'error' in p:
        print('parse error:', p.get('error'))
    else:
        print('name:', p.get('personal_info',{}).get('name'))
        print('skills:', p.get('skills')[:5])
