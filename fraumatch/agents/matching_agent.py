"""
Matching Agent - Calculates match scores and generates explanations
Uses deterministic scoring with LLM for explanations only
"""

import json
import requests
from typing import Dict, Any, List, Tuple


class MatchingAgent:
    """
    Agent that matches candidates to jobs using deterministic scoring.
    
    IMPORTANT: The numerical score comes from deterministic calculation,
    NOT from the LLM. The LLM is only used for explanations.
    """
    
    # Matching weights as specified in the project brief
    WEIGHTS = {
        "skills": 0.30,           # 30%
        "experience": 0.20,       # 20%
        "education": 0.10,        # 10%
        "languages": 0.10,        # 10%
        "location_remote": 0.10,  # 10%
        "employment_preference": 0.10,  # 10%
        "salary": 0.05,           # 5%
        "career_goals": 0.05      # 5%
    }
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.2"
    
    def find_matches(self, profile: Dict[str, Any], jobs: List[Dict[str, Any]], 
                     top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Main function: Find and rank job matches for a candidate.
        
        Args:
            profile: Structured candidate profile
            jobs: List of job listings
            top_n: Number of top matches to return
            
        Returns:
            List of matches with scores and explanations
        """
        matches = []
        
        for job in jobs:
            # Step 1: Check mandatory requirements (hard filter)
            mandatory_met = self._check_mandatory_requirements(profile, job)
            
            # Step 2: Calculate deterministic score
            score, score_breakdown = self._calculate_score(profile, job)
            
            # Step 3: Generate AI explanation (only if score > 0)
            explanation = ""
            if score > 0:
                explanation = self._generate_explanation(profile, job, score, score_breakdown)
            
            # Step 4: Create match result
            match_result = {
                "job_id": job["id"],
                "job_title": job["title"],
                "company": job["company"],
                "location": job["location"],
                "mandatory_met": mandatory_met,
                "score": round(score * 100, 1),  # Convert to percentage
                "score_breakdown": {k: round(v * 100, 1) for k, v in score_breakdown.items()},
                "explanation": explanation,
                "job_details": job["details"]
            }
            
            matches.append(match_result)
        
        # Sort by score (mandatory_met jobs first, then by score)
        matches.sort(key=lambda x: (x["mandatory_met"], x["score"]), reverse=True)
        
        return matches[:top_n]
    
    def _check_mandatory_requirements(self, profile: Dict[str, Any], job: Dict[str, Any]) -> bool:
        """
        Check if candidate meets ALL mandatory requirements.
        If any mandatory requirement fails, the job is not recommended.
        """
        mandatory = job.get("requirements", {}).get("mandatory", [])
        
        # Simple keyword matching for mandatory requirements
        profile_text = json.dumps(profile).lower()
        
        for requirement in mandatory:
            req_lower = requirement.lower()
            
            # Check for experience years requirement
            if "years" in req_lower or "experience" in req_lower:
                # Extract number of years
                import re
                numbers = re.findall(r'\d+', req_lower)
                if numbers:
                    required_years = int(numbers[0])
                    # Check if profile mentions enough experience
                    # This is simplified - in real implementation, parse work history
                    if "years" in profile_text or "experience" in profile_text:
                        continue  # Assume meets requirement for demo
                    else:
                        return False
            
            # Check for language requirements
            elif "german" in req_lower or "french" in req_lower or "english" in req_lower:
                language_found = False
                for lang in profile.get("languages", []):
                    if isinstance(lang, dict):
                        lang_name = lang.get("language", "").lower()
                        if req_lower.split()[0] in lang_name:
                            language_found = True
                            break
                if not language_found:
                    return False
            
            # Check for other requirements (skills, education, etc.)
            else:
                # Simple keyword matching
                if req_lower not in profile_text:
                    # Try partial matching
                    req_words = req_lower.split()
                    if not any(word in profile_text for word in req_words if len(word) > 3):
                        return False
        
        return True
    
    def _calculate_score(self, profile: Dict[str, Any], job: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """
        Calculate deterministic match score based on weighted criteria.
        
        Returns:
            Tuple of (total_score, score_breakdown)
        """
        scores = {}
        
        # 1. Skills matching (30%)
        scores["skills"] = self._score_skills(profile, job)
        
        # 2. Experience matching (20%)
        scores["experience"] = self._score_experience(profile, job)
        
        # 3. Education matching (10%)
        scores["education"] = self._score_education(profile, job)
        
        # 4. Languages matching (10%)
        scores["languages"] = self._score_languages(profile, job)
        
        # 5. Location/Remote compatibility (10%)
        scores["location_remote"] = self._score_location_remote(profile, job)
        
        # 6. Employment preference (10%)
        scores["employment_preference"] = self._score_employment_preference(profile, job)
        
        # 7. Salary compatibility (5%)
        scores["salary"] = self._score_salary(profile, job)
        
        # 8. Career goals (5%)
        scores["career_goals"] = self._score_career_goals(profile, job)
        
        # Calculate weighted total
        total_score = sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        
        return total_score, scores
    
    def _score_skills(self, profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        """Score based on skills match (0.0 to 1.0)."""
        profile_skills = set(s.lower() for s in profile.get("skills", []))
        job_skills = set(s.lower() for s in job.get("skills_required", []))
        
        if not job_skills:
            return 0.5  # Neutral if no skills required
        
        # Calculate overlap
        matched = profile_skills.intersection(job_skills)
        match_ratio = len(matched) / len(job_skills)
        
        return min(match_ratio * 1.2, 1.0)  # Bonus for exceeding requirements
    
    def _score_experience(self, profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        """Score based on experience match."""
        work_exp = profile.get("work_experience", [])
        
        if not work_exp:
            return 0.3  # Some credit for education
        
        # Count years of experience (simplified)
        total_years = 0
        for exp in work_exp:
            duration = exp.get("duration", "")
            # Parse duration (e.g., "2018-2022")
            if "-" in duration:
                try:
                    start, end = duration.split("-")
                    start_year = int(start.strip())
                    end_year = int(end.strip()) if end.strip().isdigit() else 2024
                    total_years += end_year - start_year
                except:
                    pass
        
        # Score based on years (assume 5 years is ideal)
        if total_years >= 5:
            return 1.0
        elif total_years >= 3:
            return 0.8
        elif total_years >= 1:
            return 0.6
        else:
            return 0.4
    
    def _score_education(self, profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        """Score based on education level."""
        education = profile.get("education", [])
        
        if not education:
            return 0.3
        
        # Check for advanced degrees
        has_masters = any("master" in edu.get("degree", "").lower() for edu in education)
        has_bachelors = any("bachelor" in edu.get("degree", "").lower() for edu in education)
        
        if has_masters:
            return 1.0
        elif has_bachelors:
            return 0.8
        else:
            return 0.5
    
    def _score_languages(self, profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        """Score based on language proficiency."""
        languages = profile.get("languages", [])
        job_requirements = job.get("requirements", {}).get("mandatory", [])
        
        # Check if required languages are present
        required_languages = []
        for req in job_requirements:
            if "german" in req.lower():
                required_languages.append("german")
            elif "french" in req.lower():
                required_languages.append("french")
            elif "english" in req.lower():
                required_languages.append("english")
        
        if not required_languages:
            return 0.8  # Neutral score if no specific requirements
        
        # Check profile languages
        profile_langs = {}
        for lang in languages:
            if isinstance(lang, dict):
                lang_name = lang.get("language", "").lower()
                level = lang.get("level", "").lower()
                profile_langs[lang_name] = level
        
        # Score each required language
        scores = []
        for req_lang in required_languages:
            if req_lang in profile_langs:
                level = profile_langs[req_lang]
                if "native" in level or "fluent" in level or "c1" in level or "c2" in level:
                    scores.append(1.0)
                elif "intermediate" in level or "b1" in level or "b2" in level:
                    scores.append(0.7)
                else:
                    scores.append(0.5)
            else:
                scores.append(0.0)
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def _score_location_remote(self, profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        """Score based on location and remote work compatibility."""
        profile_prefs = profile.get("preferences", {})
        job_details = job.get("details", {})
        
        # Check remote preference
        profile_remote = profile_prefs.get("remote_preference", "").lower()
        job_remote = job_details.get("remote_policy", "").lower()
        
        if "fully remote" in job_remote and "remote" in profile_remote:
            return 1.0
        elif "hybrid" in job_remote and ("hybrid" in profile_remote or "remote" in profile_remote):
            return 0.8
        elif "office" in job_remote and "office" in profile_remote:
            return 0.7
        elif not profile_remote:  # No preference
            return 0.6
        else:
            return 0.5
    
    def _score_employment_preference(self, profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        """Score based on employment type match (full-time vs part-time)."""
        profile_prefs = profile.get("preferences", {})
        job_details = job.get("details", {})
        
        profile_type = profile_prefs.get("employment_type", "").lower()
        job_type = job_details.get("employment_type", "").lower()
        
        if "part-time" in profile_type and "part-time" in job_type:
            return 1.0
        elif "full-time" in profile_type and "full-time" in job_type:
            return 1.0
        elif "80%" in profile_type and "80" in job_type:
            return 0.9
        elif "60%" in profile_type and "60" in job_type:
            return 0.9
        elif not profile_type:  # No preference
            return 0.6
        else:
            return 0.4
    
    def _score_salary(self, profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        """Score based on salary compatibility."""
        profile_prefs = profile.get("preferences", {})
        job_details = job.get("details", {})
        
        profile_salary = profile_prefs.get("salary_expectation", "")
        job_salary = job_details.get("salary_range", "")
        
        # Simple string matching for demo
        if not profile_salary or not job_salary:
            return 0.5
        
        # Extract numbers (simplified)
        import re
        profile_numbers = re.findall(r'\d+', profile_salary.replace(",", ""))
        job_numbers = re.findall(r'\d+', job_salary.replace(",", ""))
        
        if profile_numbers and job_numbers:
            profile_max = int(profile_numbers[-1])
            job_max = int(job_numbers[-1])
            
            if profile_max <= job_max:
                return 1.0
            elif profile_max <= job_max * 1.1:
                return 0.7
            else:
                return 0.4
        
        return 0.5
    
    def _score_career_goals(self, profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        """Score based on career goals alignment."""
        career_goals = profile.get("career_goals", "").lower()
        job_desc = job.get("description", "").lower()
        job_title = job.get("title", "").lower()
        
        if not career_goals:
            return 0.5
        
        # Simple keyword matching
        goal_keywords = career_goals.split()
        match_count = sum(1 for word in goal_keywords if len(word) > 4 and word in job_desc)
        
        if match_count > 2:
            return 0.9
        elif match_count > 0:
            return 0.7
        else:
            return 0.5
    
    def _generate_explanation(self, profile: Dict[str, Any], job: Dict[str, Any], 
                             score: float, breakdown: Dict[str, float]) -> str:
        """
        Generate AI explanation for the match.
        
        IMPORTANT: This uses the LLM only for explanation, NOT for scoring.
        """
        prompt = f"""You are a helpful HR assistant. Explain this job match to the candidate.

CANDIDATE PROFILE:
- Name: {profile.get('personal_info', {}).get('name', 'N/A')}
- Skills: {', '.join(profile.get('skills', [])[:5])}
- Experience: {len(profile.get('work_experience', []))} positions
- Location: {profile.get('personal_info', {}).get('location', 'N/A')}

JOB:
- Title: {job.get('title', 'N/A')}
- Company: {job.get('company', 'N/A')}
- Location: {job.get('location', 'N/A')}
- Required Skills: {', '.join(job.get('skills_required', [])[:5])}

MATCH SCORE: {round(score * 100)}%

SCORE BREAKDOWN:
- Skills: {round(breakdown.get('skills', 0) * 100)}%
- Experience: {round(breakdown.get('experience', 0) * 100)}%
- Languages: {round(breakdown.get('languages', 0) * 100)}%
- Location/Remote: {round(breakdown.get('location_remote', 0) * 100)}%

Write a brief, friendly explanation (3-4 sentences) of:
1. Why this is a good match (top 2-3 strengths)
2. Any areas that could be improved
3. A encouraging closing statement

Be specific and reference actual details from the profile and job.
Do NOT make up any information. Only use what is provided above."""

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 300
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            # Fallback explanation if Ollama fails
            return f"This job matches your profile with a {round(score * 100)}% score. Your skills in {', '.join(profile.get('skills', [])[:3])} align well with the position requirements."


# Test function
if __name__ == "__main__":
    agent = MatchingAgent()
    
    # Test with sample data
    test_profile = {
        "personal_info": {"name": "Sophie Müller", "location": "Basel"},
        "skills": ["Digital Marketing", "Brand Management", "SEO/SEM", "Google Analytics"],
        "work_experience": [{"duration": "2018-2022"}],
        "education": [{"degree": "Master of Science in Marketing"}],
        "languages": [{"language": "German", "level": "Native"}, {"language": "English", "level": "Fluent"}],
        "preferences": {"remote_preference": "hybrid", "employment_type": "part-time"},
        "career_goals": "Return to marketing leadership role"
    }
    
    test_job = {
        "id": "job_001",
        "title": "Marketing Manager Digital",
        "company": "Basel Pharma AG",
        "location": "Basel",
        "skills_required": ["Digital Marketing", "Brand Management", "SEO/SEM", "Google Analytics", "Team Leadership"],
        "requirements": {"mandatory": ["5+ years marketing experience", "German native or C1"]},
        "details": {"employment_type": "Full-time (100%)", "remote_policy": "Hybrid (2 days remote)"}
    }
    
    print("Testing Matching Agent...")
    matches = agent.find_matches(test_profile, [test_job])
    print(json.dumps(matches, indent=2))
