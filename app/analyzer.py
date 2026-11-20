"""Transparent, heuristic keyword alignment, NOT a real ATS prediction."""
import re
from collections import Counter
from .models import Resume

# A curated vocabulary improves relevance over counting frequent filler words.
KEYWORDS = [
 "Python", "Java", "JavaScript", "TypeScript", "React", "Angular", "Vue", "Node.js", "Next.js", "HTML", "CSS", "SQL", "NoSQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "GraphQL", "REST API", "SOAP", "Microservices", "FastAPI", "Django", "Flask", "Spring Boot", "C#", ".NET", "C++", "Go", "Kotlin", "Swift", "Ruby", "PHP", "Scala", "R", "Bash", "Git", "GitHub", "GitLab", "Jenkins", "Docker", "Kubernetes", "Terraform", "Ansible", "CI/CD", "AWS", "Azure", "GCP", "Google Cloud", "Salesforce", "Apex", "LWC", "Lightning Web Components", "SOQL", "Flows", "MuleSoft", "Copado", "Platform Events", "Selenium", "Playwright", "Cypress", "TestNG", "JUnit", "Pytest", "Cucumber", "BDD", "TDD", "API Testing", "Unit Testing", "Automation", "Agile", "Scrum", "Jira", "Confluence", "DevOps", "SonarQube", "Veracode", "Security", "OWASP", "SAST", "DAST", "Linux", "Power BI", "Tableau", "Excel", "ETL", "Spark", "Databricks", "Snowflake", "Airflow", "Kafka", "Machine Learning", "Deep Learning", "NLP", "LLM", "RAG", "LangChain", "LangGraph", "Vector Database", "Chroma", "Pinecone", "FAISS", "Gemini", "OpenAI", "Prompt Engineering", "Hugging Face", "TensorFlow", "PyTorch", "Pandas", "NumPy", "Scikit-learn", "Data Analytics", "Data Engineering", "Data Science", "Business Analytics", "Product Management", "Project Management", "Stakeholder Management", "Leadership", "Communication", "Problem Solving", "Mentoring", "System Design", "Architecture", "Performance Optimization", "Observability", "Monitoring", "Accessibility", "UX", "Figma", "Mobile Development", "Android", "iOS", "Integration", "Testing", "Documentation", "Data Visualization", "Data Modeling", "Customer Success", "Budgeting", "Forecasting", "Financial Analysis", "Supply Chain", "Marketing", "SEO", "CRM", "ERP", "Compliance", "HIPAA", "GDPR", "SOC 2", "Data Governance", "Incident Response",
]
STOP = set("""a an and are as at be been but by can candidates collaborate company cross deliver demonstrate description develop developing do each effective ensure experience for from has have in including is it job knowledge looking must of on or our own please preferred qualifications required responsibilities role should strong such team that the their them these this to using we will with work working you your years ability able good excellent proven understanding skills familiarity hands hands-on plus nice ideal building build solution solutions create creating support design implement lead leading maintain designing leveraging across within candidate professional perform use used track record high quality relevant best practices technical fast paced related requirements tools technology technologies""".split())
ALIASES = {
 "node.js": ["nodejs", "node.js"],
 "javascript": ["javascript", "js", "ecmascript"],
 "typescript": ["typescript", "ts"],
 "ci/cd": ["ci/cd", "continuous integration", "continuous deployment", "continuous delivery"],
 "aws": ["aws", "amazon web services"],
 "gcp": ["gcp", "google cloud platform", "google cloud"],
 "salesforce": ["salesforce", "sfdc"],
 "lwc": ["lwc", "lightning web components"],
 "rest api": ["rest api", "restful", "rest apis"],
 "llm": ["llm", "large language model", "large language models"],
 "rag": ["rag", "retrieval augmented generation", "retrieval-augmented generation"],
 "power bi": ["power bi", "powerbi"],
 "sql": ["sql", "structured query language"],
 "react": ["react", "reactjs", "react.js"],
 "ml": ["ml", "machine learning"],
 "apex": ["apex", "salesforce apex"],
}


def contains(text: str, phrase: str) -> bool:
    variants = ALIASES.get(phrase.lower(), [phrase])
    for v in variants:
        if re.search(r"(?<![a-zA-Z0-9])" + re.escape(v) + r"(?![a-zA-Z0-9])", text, re.I):
            return True
    return False


def extract_terms(jd: str) -> list[str]:
    vocab = [term for term in KEYWORDS if contains(jd, term)]
    found = {t.lower() for t in vocab}
    # Extract prominent role-specific terms not captured by the curated vocabulary.
    tokens = re.findall(r"[A-Za-z][A-Za-z+#./-]*", jd.lower())
    freq = Counter(t.strip("./-") for t in tokens if len(t) >= 5 and t not in STOP)
    dynamic = [t for t, count in freq.most_common(30) if count >= 2 and t not in found and not t.isdigit()]
    result = vocab + [term.title() for term in dynamic]
    return result[:32]


def analyze(resume: Resume, jd: str) -> dict:
    terms = extract_terms(jd)
    source = resume.flattened()
    matched = [term for term in terms if contains(source, term)]
    missing = [term for term in terms if not contains(source, term)]
    score = round((len(matched) / len(terms) * 100)) if terms else 0
    sections = {k: len(resume.sections.get(k, "").strip()) > 0 for k in resume.sections}
    tips = []
    if missing:
        tips.append("Review missing keywords and add only skills you genuinely have.")
    if not resume.sections.get("summary", "").strip():
        tips.append("Add a concise, role-specific professional summary.")
    if not resume.sections.get("experience", "").strip() and not resume.sections.get("projects", "").strip():
        tips.append("Include experience or projects that demonstrate your qualifications.")
    if not re.search(r"\b\d+(?:%|\+|\s*(?:months|years|users|hours|projects))\b", source, re.I):
        tips.append("Consider measurable outcomes when you have accurate numbers to support them.")
    if not terms:
        tips.append("Paste a fuller job description for a more useful comparison.")
    return {
        "score": score,
        "matched": matched,
        "missing": missing,
        "total": len(terms),
        "tips": tips[:4],
        "disclaimer": "Heuristic keyword overlap only. This is not an ATS score, interview probability, or hiring prediction.",
    }


def audit_proposals(resume: Resume, jd: str, proposals: dict[str, str]) -> dict[str, list[str]]:
    """Conservative, explainable warnings. This cannot prove factual correctness."""
    original_all = resume.flattened()
    jd_terms = extract_terms(jd)
    reports = {}
    for section, proposal in proposals.items():
        old = resume.sections.get(section, "")
        warnings = []
        # Added numerals often imply unsupported achievements, dates or credentials.
        source_numbers = set(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?%?(?!\w)", original_all))
        proposal_numbers = set(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?%?(?!\w)", proposal))
        added_numbers = sorted(proposal_numbers - source_numbers)
        if added_numbers:
            warnings.append("New numeric details detected (" + ", ".join(added_numbers[:7]) + "). Verify dates, metrics and years.")
        added_skills = [term for term in jd_terms if contains(proposal, term) and not contains(original_all, term)]
        if added_skills:
            warnings.append("New job keywords not found in your source resume: " + ", ".join(added_skills[:8]) + ". Confirm these are genuine skills.")
        if len(old.strip()) >= 150 and len(proposal.strip()) < .4 * len(old.strip()):
            warnings.append("This draft is substantially shorter. Check for missing achievements or responsibilities.")
        reports[section] = warnings
    return reports
