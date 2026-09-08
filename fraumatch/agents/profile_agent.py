"""
Profile Agent - Extracts structured information from CV text

Two modes:
1. extract_profile_main() - Fast, deterministic rule-based extraction (ALWAYS works, no AI needed)
2. extract_profile() - Uses Ollama (optional) with rule-based fallback

For a reliable classroom demo, use extract_profile_main() - it's instant and complete.
"""

import json
import re
from typing import Dict, Any, List


# Swiss locations and common keywords for extraction
SWISS_CITIES = [
    "Zurich", "Zürich", "Basel", "Geneva", "Genf", "Bern", "Lausanne",
    "Lucerne", "Luzern", "St. Gallen", "Winterthur", "Fribourg", "Neuchatel"
]

# Expanded skill database organized by category
SKILL_CATEGORIES = {
    "Digital Marketing": ["digital marketing", "seo", "sem", "google analytics", "google ads",
                          "social media", "content marketing", "email marketing", "ppc"],
    "Marketing": ["brand management", "branding", "market research", "product launch",
                  "advertising", "marketing strategy"],
    "Project Management": ["project management", "agile", "scrum", "pmp", "product management",
                           "stakeholder management", "budget management"],
    "Leadership": ["team leadership", "team management", "leadership", "mentoring"],
    "Frontend Development": ["react", "typescript", "javascript", "angular", "html", "css"],
    "Backend Development": ["node.js", "nodejs", "python", "java", "restful api", "backend"],
    "Database": ["sql", "postgresql", "mongodb", "mysql", "database design"],
    "DevOps": ["docker", "kubernetes", "aws", "azure", "ci/cd", "devops", "cloud computing"],
    "Data & Analytics": ["data analysis", "power bi", "tableau", "spss", "advanced excel"],
    "HR": ["recruitment", "employee relations", "onboarding", "performance management",
           "training & development", "compensation management"],
    "Labor Law": ["swiss labor law", "hr compliance"],
    "HRIS": ["hris", "workday", "successfactors", "sap hcm"],
    "Finance": ["financial analysis", "financial modeling", "financial reporting", "forecasting"],
    "Accounting": ["financial statements", "audit", "taxation", "ifrs", "gaap", "accounts payable"],
    "ERP": ["sap", "sap fico", "sap fi"],
    "Content": ["content creation", "copywriting", "content writing"],
}

# Language proficiency levels (high to low)
LANG_LEVELS = [
    ("native", 1.0), ("fluent", 0.95), ("c1", 0.9), ("c2", 0.9),
    ("advanced", 0.85), ("b2", 0.75), ("intermediate", 0.7), ("b1", 0.65),
    ("basic", 0.4), ("a2", 0.4), ("a1", 0.3)
]

# Known degree patterns
DEGREE_PATTERNS = [
    ("doctor", "PhD"),
    ("master", "Master's Degree"),
    ("mba", "MBA"),
    ("bachelor", "Bachelor's Degree"),
    ("bsc", "Bachelor's Degree"),
    ("ba ", "Bachelor's Degree"),
    ("licence", "Bachelor's Degree"),
    ("diploma", "Diploma"),
    ("certificate", "Certificate"),
]


class ProfileAgent:
    """Agent that converts unstructured CV text into a structured professional profile."""

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.2"

    # ------------------------------------------------------------------ #
    # MAIN ENTRY POINT (used by the app - fast, no AI required)
    # ------------------------------------------------------------------ #
    def extract_profile_main(self, cv_text: str) -> Dict[str, Any]:
        """
        Fast, deterministic, complete profile extraction using rules.
        This ALWAYS works instantly and never depends on AI.
        """
        text = cv_text
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        profile = {
            "personal_info": {
                "name": self._extract_name(lines),
                "location": self._extract_location(text),
                "email": self._extract_email(text),
                "phone": self._extract_phone(text)
            },
            "summary": self._extract_summary(text),
            "work_experience": self._extract_experience(lines),
            "education": self._extract_education(lines),
            "skills": self._extract_skills(text),
            "languages": self._extract_languages(text),
            "certifications": self._extract_certifications(text),
            "preferences": self._extract_preferences(text),
            "career_goals": self._extract_career_goals(text),
        }

        return profile

    # ------------------------------------------------------------------ #
    # OPTIONAL AI extraction (with rule-based fallback)
    # ------------------------------------------------------------------ #
    def extract_profile(self, cv_text: str) -> Dict[str, Any]:
        """Try AI extraction, fall back to fast rule-based extraction if it fails."""
        try:
            prompt = self._create_extraction_prompt(cv_text)
            response = self._call_ollama(prompt)
            profile = self._parse_response(response)
            if "error" not in profile:
                return profile
        except Exception:
            pass
        # Fall back to deterministic extraction
        return self.extract_profile_main(cv_text)

    # ------------------------------------------------------------------ #
    # Extraction helpers
    # ------------------------------------------------------------------ #
    def _extract_name(self, lines: List[str]) -> str:
        """Extract name from the first non-empty line (or a line with 2 capitalized words)."""
        for line in lines:
            # Name line: 2-4 words, all capitalized, no special chars
            words = line.split()
            if 2 <= len(words) <= 4:
                if all(w[:1].isupper() for w in words) and not any(
                    c in line for c in ["@", "|", "+", "(", ")", "PROF", "SUMMARY", "EXPERIENCE"]
                ):
                    return line
        return "N/A"

    def _extract_email(self, text: str) -> str:
        """Extract email address."""
        match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
        return match.group(0) if match else "N/A"

    def _extract_phone(self, text: str) -> str:
        """Extract phone number (Swiss or international format, full number)."""
        # Swiss mobile: +41 7x xxx xx xx; also general international
        match = re.search(r'\+?\d{1,3}[\s.-]?\d{2,3}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}', text)
        if match:
            return match.group(0)
        return "N/A"

    def _extract_location(self, text: str) -> str:
        """Find location - look for Swiss cities near the top (profile header)."""
        # Search the first 600 chars (profile header area)
        header = text[:600].lower()
        # Also check the first 3 lines specifically
        lines = [l.lower() for l in text.split("\n")[:4]]

        # Priority: search profile header lines first (before email/contact line)
        for line in lines:
            for city in SWISS_CITIES:
                if city.lower() in line:
                    return city if city != "Zürich" else "Zurich"

        # Fallback: search broader header area
        for city in SWISS_CITIES:
            if city.lower() in header:
                return city if city != "Zürich" else "Zurich"
        return "N/A"

    def _extract_summary(self, text: str) -> str:
        """Extract professional summary."""
        # Look specifically in the summary section
        lower = text.lower()
        # Find text between "PROFESSIONAL SUMMARY" and "WORK EXPERIENCE"
        summary_match = re.search(r'professional summary[:\n]*\s*([^\n]+)', lower)
        if summary_match and len(summary_match.group(1).strip()) > 3:
            return summary_match.group(1).strip()

        # Fallback: first substantial paragraph that isn't a header or contact
        paragraphs = re.split(r'\n\s*\n', text)
        for para in paragraphs:
            lines = [l.strip() for l in para.split("\n") if l.strip()]
            for line in lines:
                if any(w in line.upper() for w in ["PROFESSIONAL SUMMARY", "SUMMARY", "WORK EXPERIENCE", "EDUCATION", "SKILLS", "CAREER", "PREFERENCES"]):
                    continue
                if '@' in line or '|' in line or line.startswith('-'):
                    continue
                if len(line.split()) > 5 and not line.isupper():
                    return line
        return "N/A"

    def _extract_experience(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract work experience entries."""
        experiences = []
        current = None

        for line in lines:
            line_lower = line.lower()
            # Stop collecting achievements at section headers
            if current and any(
                h in line_lower for h in ["education", "languages", "skills", "certification",
                                          "certificates", "preferences", "career goals", "work experience"]
            ):
                experiences.append(current)
                current = None
                # Continue scanning - subsequent lines before the next role will just be skipped
                continue

            # Skip education lines (they match the experience pattern but aren't work)
            if any(k in line_lower for k in ["master of", "bachelor of", "mba", "phd", "doctor of"]):
                continue

            # Detect a new role line: "Title | Company | Years" or "Title | Company | Year-Year"
            match = re.match(
                r'^([A-Z][A-Za-z\s/&]+?)\s*[|–—-]\s*([A-Za-z\s&\.]+?)\s*[|–—-]\s*(\d{4}(?:\s*[–\-]\s*\d{4}|[–\-]Present|–Present| to \d{4})?)$',
                line
            )
            if match:
                if current:
                    experiences.append(current)
                title = match.group(1).strip()
                company = match.group(2).strip()
                duration = match.group(3).strip()
                current = {
                    "title": title,
                    "company": company,
                    "duration": duration,
                    "key_achievements": []
                }
            elif current and line.startswith("-"):
                # Bullet point = achievement
                current["key_achievements"].append(line.lstrip("- "))
            elif current and re.match(r'^[A-Z]', line) and len(line) < 60:
                # Additional line that might be part of the title/context
                if not re.match(r'^[A-Z ]{5,}$', line):  # not a header
                    current["key_achievements"].append("- " + line)

        if current:
            experiences.append(current)

        return experiences

    def _extract_education(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract education entries."""
        education = []

        for line in lines:
            # Look for lines with degree + university + year
            has_degree = any(k in line.lower() for k in ["master", "bachelor", "mba", "doctor", "phd", "bsc", "diploma", "degree"])
            has_institution = any(k in line.lower() for k in ["university", "college", "eth", "école", "school", "institut", "institute", "bocconi", "st. gallen", "hsg"])
            has_year = bool(re.search(r'\b(19|20)\d{2}\b', line))

            if has_degree:
                year_match = re.search(r'\b(19|20)\d{2}\b', line)
                # Try to split "Degree | Institution | Year"
                parts = re.split(r'\s*[|–—-]\s*', line)
                if len(parts) >= 2:
                    degree = parts[0].strip()
                    institution = parts[1].strip() if len(parts) > 1 else ""
                    year = year_match.group(0) if year_match else ""
                    education.append({
                        "degree": degree,
                        "institution": institution,
                        "year": year
                    })

        return education

    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from known skill database (word-boundary matching)."""
        found = []
        text_lower = text.lower()

        for category, keywords in SKILL_CATEGORIES.items():
            for keyword in keywords:
                # Use word boundaries; for multi-word keywords match as a phrase
                escaped = re.escape(keyword)
                pattern = r'(?<![a-z])' + escaped + r'(?![a-z])'
                if re.search(pattern, text_lower):
                    # Normalize skill name (capitalize first letter, handle special cases)
                    skill = self._normalize_skill(keyword)
                    if skill and skill not in found:
                        found.append(skill)

        return found

    def _normalize_skill(self, skill: str) -> str:
        """Normalize skill display name."""
        # Handle acronyms and known special cases
        special = {
            "seo": "SEO", "sem": "SEM", "sql": "SQL", "api": "API", "html": "HTML",
            "css": "CSS", "aws": "AWS", "sap": "SAP", "hris": "HRIS", "ifrs": "IFRS",
            "gaap": "GAAP", "ppc": "PPC", "hr": "HR", "ci/cd": "CI/CD"
        }
        for key, value in special.items():
            if skill.lower() == key or skill.lower().startswith(key + " "):
                return skill.replace(key, value, 1) if skill.lower() != key else value

        # Normal case: capitalize each word
        return skill.title()

    def _extract_languages(self, text: str) -> List[Dict[str, str]]:
        """Extract languages and proficiency levels."""
        languages = []
        known_languages = ["german", "english", "french", "italian", "spanish", "portuguese", "swiss german"]

        lines = [l.strip() for l in text.lower().split("\n") if l.strip()]

        for line in lines:
            found_lang = None
            for lang in known_languages:
                if lang in line and re.search(r'\b' + lang + r'\b', line):
                    found_lang = lang
                    break

            if found_lang:
                level = "N/A"
                # Look for proficiency markers anywhere in the line
                for lvl_name, _ in LANG_LEVELS:
                    if lvl_name in line:
                        level = lvl_name.upper()
                        break
                if level == "N/A":
                    # Try to find parenthetical level like (C1), (B2)
                    match = re.search(r'\(?([ABCE]\d)\)?', line)
                    if match:
                        level = match.group(1).upper()

                # Normalize language name
                display_name = found_lang.title()
                if found_lang == "swiss german":
                    display_name = "Swiss German"

                languages.append({"language": display_name, "level": level})

        return languages

    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certifications."""
        certs = []
        cert_keywords = ["certified", "certification", "certificate", "aws certified", "shrm",
                         "google analytics certified", "hubspot", "pmp", "cpa"]
        skip_headers = ["certifications", "certification", "certificates"]
        lines = text.split("\n")

        for line in lines:
            lower = line.strip().lower()
            # Skip headers / section titles
            if lower in skip_headers or line.strip().isupper():
                continue
            for keyword in cert_keywords:
                if keyword in lower:
                    cleaned = line.strip("- ").strip()
                    if cleaned and cleaned not in certs and len(cleaned) > 3:
                        certs.append(cleaned)
                    break
        return certs

    def _extract_preferences(self, text: str) -> Dict[str, str]:
        """Extract job preferences (employment type, remote, location, salary)."""
        prefs = {
            "employment_type": self._extract_employment_type(text),
            "remote_preference": self._extract_remote_preference(text),
            "location_constraint": self._extract_location_constraint(text),
            "salary_expectation": self._extract_salary(text)
        }
        return prefs

    def _extract_employment_type(self, text: str) -> str:
        """Extract employment type preference (part/full time, percentage)."""
        lower = text.lower()
        if "part-time" in lower or "part time" in lower:
            # Try to extract percentage
            pct = re.search(r'(50|60|70|80|90|100)\s*%', lower)
            return f"Part-time{pct.group(0) if pct else ''}"
        elif "full-time" in lower or "full time" in lower:
            return "Full-time"
        elif re.search(r'\b(\d{2,3})\s*%', lower):
            pct = re.search(r'\b(\d{2,3})\s*%', lower)
            return f"{pct.group(1)}%"
        return "N/A"

    def _extract_remote_preference(self, text: str) -> str:
        """Extract remote/hybrid/office preference."""
        lower = text.lower()
        if "fully remote" in lower or "remote preferred" in lower:
            return "Remote"
        elif "hybrid" in lower:
            return "Hybrid"
        elif "remote" in lower:
            return "Remote"
        elif "office" in lower:
            return "Office"
        return "N/A"

    def _extract_location_constraint(self, text: str) -> str:
        """Extract location constraints (commute, city)."""
        city = self._extract_location(text)
        lower = text.lower()
        # Look for commute constraints
        if "commute" in lower:
            match = re.search(r'[^\n]*commute[^\n]*', lower)
            if match:
                return match.group(0).strip()
        elif "max" in lower and "min" in lower:
            match = re.search(r'max [^\n]*', lower)
            if match:
                return match.group(0).strip()
        return city if city != "N/A" else "N/A"

    def _extract_salary(self, text: str) -> str:
        """Extract salary expectation."""
        lower = text.lower()
        match = re.search(r'salary[^:]*:\s*\n?\s*([A-Za-z0-9.,\s\-–]+)', lower, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # Alternative: look for any currency amount
        match = re.search(r'(chf|usd|eur|euro)\s?[\d,\.]+\s?-\s?[\d,\.]+', lower, re.IGNORECASE)
        if match:
            return match.group(0).upper()
        return "N/A"

    def _extract_career_goals(self, text: str) -> str:
        """Extract career goals."""
        lower = text.lower()
        # Look for career goals section
        match = re.search(r'career goals?\s*:?\s*\n?\s*([^\n]+)', lower)
        if match:
            return match.group(1).strip()
        # Look for "seeking" or "looking to"
        match = re.search(r'(?:seeking|looking to|return to|continue as|interested in)[^\n]*', lower)
        if match:
            return match.group(0).strip()
        return "N/A"

    # ------------------------------------------------------------------ #
    # (Legacy / optional AI methods - kept for reference but not used by default)
    # ------------------------------------------------------------------ #
    def _create_extraction_prompt(self, cv_text: str) -> str:
        # (AI prompt - kept but not used in fast demo mode)
        return ""

    def _call_ollama(self, prompt: str) -> str:
        return '{"error": "AI disabled in fast demo mode"}'

    def _parse_response(self, response: str) -> Dict[str, Any]:
        return {"error": "AI disabled in fast demo mode"}


# Compatibility alias
def extract_profile_simple(self, cv_text):
    """Alias for extract_profile_main."""
    return self.extract_profile_main(cv_text)


# Test function
if __name__ == "__main__":
    agent = ProfileAgent()

    with open('data/sample_cvs.json', encoding='utf-8') as f:
        cvs = json.load(f)

    for cv in cvs:
        print("=" * 50)
        print("PROFILE FOR:", cv["name"])
        result = agent.extract_profile_main(cv["cv_text"])
        print(json.dumps(result, indent=2, ensure_ascii=False))
