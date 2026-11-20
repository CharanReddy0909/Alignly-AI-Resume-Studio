from typing import Literal
from pydantic import BaseModel, Field, field_validator

SECTIONS = [
    "summary", "experience", "skills", "projects", "education",
    "achievements", "certifications", "additional",
]


class Resume(BaseModel):
    name: str = Field(default="", max_length=220)
    headline: str = Field(default="", max_length=250)
    email: str = Field(default="", max_length=220)
    phone: str = Field(default="", max_length=100)
    location: str = Field(default="", max_length=200)
    links: str = Field(default="", max_length=400)
    sections: dict[str, str] = Field(default_factory=dict)

    @field_validator("sections")
    @classmethod
    def valid_sections(cls, value):
        if not isinstance(value, dict):
            raise ValueError("Sections must be an object")
        for key, text in value.items():
            if key not in SECTIONS:
                raise ValueError(f"Unknown section: {key}")
            if len(text) > 30000:
                raise ValueError(f"Section {key} exceeds 30,000 characters")
        return value

    def flattened(self) -> str:
        return "\n".join([
            self.name, self.headline, self.email, self.phone,
            self.location, self.links,
            *[self.sections.get(k, "") for k in SECTIONS],
        ])


class AnalysisRequest(BaseModel):
    resume: Resume
    job_description: str = Field(min_length=30, max_length=60000)


class EnhanceRequest(AnalysisRequest):
    sections_to_change: list[str] = Field(min_length=1)
    provider: Literal["gemini", "ollama"] = "gemini"
    custom_instructions: str = Field(default="", max_length=1500)

    @field_validator("sections_to_change")
    @classmethod
    def valid_selected_sections(cls, value):
        if any(section not in SECTIONS for section in value):
            raise ValueError("Unsupported section selected")
        return list(dict.fromkeys(value))


class ExportRequest(BaseModel):
    resume: Resume
    template: Literal["classic", "modern", "compact"] = "modern"
    format: Literal["pdf", "docx"] = "pdf"
