"""
Application Agent - Generates tailored application materials
Uses verified candidate information only - never invents facts
"""

import json
import requests
from typing import Dict, Any


class ApplicationAgent:
    """
    Agent that generates tailored application materials.
    
    IMPORTANT RULES:
    - Only uses verified candidate information
    - Never invents experience, qualifications, or skills
    - Candidate must approve before submission
    """
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.2"
    
    def generate_application(self, profile: Dict[str, Any], job: Dict[str, Any],
                             use_ai: bool = True) -> Dict[str, str]:
        """
        Main function: Generate tailored application materials.
        
        Args:
            profile: Verified candidate profile
            job: Target job listing
            use_ai: If True, use LLM for the cover letter. If False, use
                    a fast deterministic cover letter (no AI needed).
            
        Returns:
            Dictionary with cover letter, CV summary, and application notes
        """
        application = {
            "cover_letter": self._generate_cover_letter(profile, job, use_ai=use_ai),
            "cv_summary": self._generate_cv_summary(profile, job),
            "application_notes": self._generate_application_notes(profile, job),
            "disclaimer": self._get_disclaimer()
        }
        
        return application
    
    def _generate_cover_letter(self, profile: Dict[str, Any], job: Dict[str, Any],
                               use_ai: bool = True) -> str:
        """Generate a tailored cover letter using only verified information."""
        if not use_ai:
            return self._fallback_cover_letter(profile, job)
        
        # Extract verified information from profile
        name = profile.get("personal_info", {}).get("name", "[Candidate Name]")
        skills = profile.get("skills", [])
        work_exp = profile.get("work_experience", [])
        education = profile.get("education", [])
        languages = profile.get("languages", [])
        career_goals = profile.get("career_goals", "")
        
        # Get job details
        job_title = job.get("title", "[Job Title]")
        company = job.get("company", "[Company]")
        job_skills = job.get("skills_required", [])
        
        # Create the prompt with ONLY verified information
        prompt = f"""You are a professional HR assistant writing a cover letter.

IMPORTANT RULES:
- Only use the information provided below
- Do NOT add any information not in the verified data
- Do NOT invent experiences, achievements, or skills
- Keep it professional and concise (250-300 words)

VERIFIED CANDIDATE INFORMATION:
Name: {name}
Skills: {', '.join(skills[:8])}
Work Experience: {len(work_exp)} positions
Education: {', '.join([e.get('degree', '') for e in education[:2]])}
Languages: {', '.join([f"{l.get('language', '')} ({l.get('level', '')})" for l in languages[:3]])}
Career Goals: {career_goals if career_goals else 'Seeking suitable opportunities'}

TARGET JOB:
Position: {job_title}
Company: {company}
Required Skills: {', '.join(job_skills[:5])}

Write a professional cover letter that:
1. Opens with enthusiasm for the specific position
2. Highlights 2-3 most relevant skills from the verified data
3. Mentions relevant experience (only what is in the work experience)
4. Shows alignment with career goals
5. Closes with interest in discussing further

Use a professional but warm tone. Write in English."""

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 500
                    }
                },
                timeout=45
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            return self._fallback_cover_letter(profile, job)
    
    def _generate_cv_summary(self, profile: Dict[str, Any], job: Dict[str, Any]) -> str:
        """Generate a tailored CV summary for this specific job."""
        
        skills = profile.get("skills", [])
        work_exp = profile.get("work_experience", [])
        job_skills = job.get("skills_required", [])
        
        # Create a tailored summary
        summary_parts = []
        
        # Add relevant skills
        relevant_skills = [s for s in skills if s.lower() in [js.lower() for js in job_skills]]
        if relevant_skills:
            summary_parts.append(f"Key Skills: {', '.join(relevant_skills[:5])}")
        
        # Add experience summary
        if work_exp:
            latest_exp = work_exp[0]
            summary_parts.append(f"Recent Role: {latest_exp.get('title', 'N/A')} at {latest_exp.get('company', 'N/A')}")
        
        # Add education
        education = profile.get("education", [])
        if education:
            summary_parts.append(f"Education: {education[0].get('degree', 'N/A')}")
        
        return " | ".join(summary_parts) if summary_parts else "Professional with relevant experience and skills."
    
    def _generate_application_notes(self, profile: Dict[str, Any], job: Dict[str, Any]) -> str:
        """Generate notes for the candidate about the application."""
        
        notes = []
        
        # Add interview preparation tips
        notes.append("INTERVIEW PREPARATION:")
        notes.append("- Review your key achievements in previous roles")
        notes.append("- Prepare examples of how your skills match this position")
        notes.append("- Research the company and its recent projects")
        
        # Add specific tips based on job requirements
        job_skills = job.get("skills_required", [])
        profile_skills = profile.get("skills", [])
        
        missing_skills = [s for s in job_skills if s.lower() not in [ps.lower() for ps in profile_skills]]
        if missing_skills:
            notes.append(f"\nAREAS TO ADDRESS:")
            notes.append(f"- The job requires: {', '.join(missing_skills)}")
            notes.append("- Consider how your transferable skills apply")
        
        return "\n".join(notes)
    
    def _fallback_cover_letter(self, profile: Dict[str, Any], job: Dict[str, Any]) -> str:
        """Generate a basic cover letter if AI is unavailable."""
        
        name = profile.get("personal_info", {}).get("name", "[Candidate Name]")
        job_title = job.get("title", "[Position]")
        company = job.get("company", "[Company]")
        skills = profile.get("skills", [])
        
        return f"""Dear Hiring Manager,

I am writing to express my interest in the {job_title} position at {company}.

With my background in {', '.join(skills[:3]) if skills else 'relevant fields'}, I believe I would be a strong candidate for this role. My experience has equipped me with the skills necessary to contribute effectively to your team.

I am particularly drawn to this opportunity because it aligns with my career goals and offers the chance to work with a reputable organization like {company}.

I would welcome the opportunity to discuss how my qualifications align with your needs. Thank you for considering my application.

Best regards,
{name}"""
    
    def _get_disclaimer(self) -> str:
        """Return the disclaimer about AI-generated content."""
        return """⚠️ IMPORTANT DISCLAIMER:
This application material was generated by AI using ONLY your verified profile information.

Please review carefully before submitting:
- Verify all facts are accurate
- Ensure the tone matches your style
- Add any personal touches you want
- Do NOT submit without your approval

MATCHA does NOT automatically submit applications to employers."""


# Test function
if __name__ == "__main__":
    agent = ApplicationAgent()
    
    test_profile = {
        "personal_info": {"name": "Sophie Müller"},
        "skills": ["Digital Marketing", "Brand Management", "SEO/SEM", "Google Analytics"],
        "work_experience": [{"title": "Senior Marketing Manager", "company": "Roche Pharma", "duration": "2018-2022"}],
        "education": [{"degree": "Master of Science in Marketing"}],
        "languages": [{"language": "German", "level": "Native"}, {"language": "English", "level": "Fluent"}],
        "career_goals": "Return to marketing leadership role"
    }
    
    test_job = {
        "title": "Marketing Manager Digital",
        "company": "Basel Pharma AG",
        "skills_required": ["Digital Marketing", "Brand Management", "SEO/SEM"]
    }
    
    print("Testing Application Agent...")
    result = agent.generate_application(test_profile, test_job)
    print("\nCOVER LETTER:")
    print(result["cover_letter"])
    print("\nCV SUMMARY:")
    print(result["cv_summary"])
    print("\nDISCLAIMER:")
    print(result["disclaimer"])
