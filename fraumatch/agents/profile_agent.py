"""
Profile Agent - Extracts structured information from CV text
Uses Ollama (local AI) to analyze and structure candidate profiles
"""

import json
import requests
from typing import Dict, Any


class ProfileAgent:
    """Agent that converts unstructured CV text into a structured profile."""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.2"  # Free, runs locally
    
    def extract_profile(self, cv_text: str) -> Dict[str, Any]:
        """
        Main function: Takes raw CV text, returns structured profile.
        
        Args:
            cv_text: The full text of the candidate's CV
            
        Returns:
            Dictionary with structured profile information
        """
        # Step 1: Create the prompt for the AI
        prompt = self._create_extraction_prompt(cv_text)
        
        # Step 2: Call Ollama (local AI)
        response = self._call_ollama(prompt)
        
        # Step 3: Parse the response into structured data
        profile = self._parse_response(response)
        
        return profile
    
    def _create_extraction_prompt(self, cv_text: str) -> str:
        """Creates the AI prompt for profile extraction."""
        return f"""You are a professional HR assistant. Extract structured information from this CV.

IMPORTANT RULES:
- Only extract information that is explicitly stated in the CV
- Do NOT infer or guess information
- Do NOT make up information that is not in the CV
- If information is not available, use "N/A"

CV TEXT:
{cv_text}

Extract and return ONLY a valid JSON object with this exact structure:
{{
    "personal_info": {{
        "name": "full name",
        "location": "city, country",
        "email": "email address",
        "phone": "phone number"
    }},
    "summary": "brief professional summary (2-3 sentences)",
    "work_experience": [
        {{
            "title": "job title",
            "company": "company name",
            "duration": "time period",
            "key_achievements": ["achievement 1", "achievement 2"]
        }}
    ],
    "education": [
        {{
            "degree": "degree name",
            "institution": "school name",
            "year": "graduation year"
        }}
    ],
    "skills": ["skill 1", "skill 2", "skill 3"],
    "languages": [
        {{
            "language": "language name",
            "level": "proficiency level"
        }}
    ],
    "certifications": ["certification 1", "certification 2"],
    "preferences": {{
        "employment_type": "full-time/part-time/preference",
        "remote_preference": "remote/hybrid/office",
        "location_constraint": "location details",
        "salary_expectation": "salary range if mentioned"
    }},
    "career_goals": "career objectives if mentioned"
}}

Return ONLY the JSON, no additional text."""
    
    def _call_ollama(self, prompt: str) -> str:
        """Calls the local Ollama API."""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistent results
                        "num_predict": 1000
                    }
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()["response"]
        except requests.exceptions.ConnectionError:
            return json.dumps({"error": "Cannot connect to Ollama. Please make sure Ollama is running."})
        except Exception as e:
            return json.dumps({"error": f"Error calling Ollama: {str(e)}"})
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parses the AI response into a structured dictionary."""
        try:
            # Try to extract JSON from the response
            # Sometimes AI adds extra text, so we find the JSON part
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {"error": "Could not parse AI response", "raw_response": response}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON in AI response", "raw_response": response}
    
    def extract_profile_simple(self, cv_text: str) -> Dict[str, Any]:
        """
        Simple rule-based extraction (backup if Ollama is not available).
        Uses basic text parsing without AI.
        """
        profile = {
            "personal_info": {
                "name": "N/A",
                "location": "N/A",
                "email": "N/A",
                "phone": "N/A"
            },
            "summary": "N/A",
            "work_experience": [],
            "education": [],
            "skills": [],
            "languages": [],
            "certifications": [],
            "preferences": {},
            "career_goals": "N/A"
        }
        
        lines = cv_text.split('\n')
        
        # Extract name (first line)
        if lines:
            profile["personal_info"]["name"] = lines[0].strip()
        
        # Extract email
        for line in lines:
            if '@' in line and ('.' in line):
                profile["personal_info"]["email"] = line.strip()
                break
        
        # Extract phone (basic pattern)
        for line in lines:
            if any(char.isdigit() for char in line) and ('+' in line or '0' in line):
                if len(line) > 8:
                    profile["personal_info"]["phone"] = line.strip()
                    break
        
        # Extract location (look for Swiss cities)
        swiss_cities = ['Zurich', 'Basel', 'Geneva', 'Bern', 'Lausanne', 'Lucerne', 'St. Gallen']
        for line in lines:
            for city in swiss_cities:
                if city.lower() in line.lower():
                    profile["personal_info"]["location"] = city
                    break
        
        # Extract skills (look for common skill patterns)
        skill_keywords = ['python', 'javascript', 'react', 'node.js', 'sql', 'excel', 
                         'marketing', 'seo', 'social media', 'project management',
                         'hr', 'recruitment', 'accounting', 'finance']
        for line in lines:
            for skill in skill_keywords:
                if skill.lower() in line.lower():
                    profile["skills"].append(skill.title())
        
        # Remove duplicates
        profile["skills"] = list(set(profile["skills"]))
        
        return profile


# Test function
if __name__ == "__main__":
    agent = ProfileAgent()
    
    # Test with sample CV
    test_cv = """Sophie Müller
Basel, Switzerland
sophie.mueller@email.ch | +41 76 123 45 67

PROFESSIONAL SUMMARY
Experienced marketing professional with 8 years of experience.

WORK EXPERIENCE
Senior Marketing Manager | Roche Pharma | 2018-2022
- Led digital marketing campaigns

EDUCATION
Master of Science in Marketing | University of St. Gallen | 2015

SKILLS
Digital Marketing, Brand Management, SEO/SEM, Google Analytics
"""
    
    print("Testing Profile Agent...")
    result = agent.extract_profile(test_cv)
    print(json.dumps(result, indent=2))
