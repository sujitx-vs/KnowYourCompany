"""Validated public brief schema shared by the browser and PDF renderer."""
from typing import Literal
from pydantic import BaseModel, Field, field_validator

Confidence = Literal["HIGH", "MEDIUM", "LOW", "INSUFFICIENT"]


class Identity(BaseModel):
    name: str = Field(max_length=180)
    location: str = Field(max_length=250)
    industry: str = Field(max_length=250)
    website: str = Field(max_length=500)
    confidence: Confidence
    reason: str = Field(max_length=700)


class Relevance(BaseModel):
    relevant_indexes: list[int] = Field(max_length=30)


class Claim(BaseModel):
    text: str = Field(min_length=1, max_length=2200)
    kind: Literal["fact", "recommendation", "limitation"]
    source_ids: list[str] = Field(max_length=15)

    @field_validator("source_ids", mode="before")
    @classmethod
    def unique_sources(cls, value):
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return list(dict.fromkeys(value))
        return value


class Section(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    claims: list[Claim] = Field(min_length=1, max_length=10)


class Domain(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=500)
    source_ids: list[str] = Field(min_length=1, max_length=8)


class Brief(BaseModel):
    confidence: Confidence
    summary: str = Field(max_length=700, description="Describe evidence coverage and limitations, not uncited company facts")
    sections: list[Section] = Field(max_length=10)
    domains: list[Domain] = Field(max_length=8, description="Company brief only; empty for domain preparation")


class CitationError(ValueError):
    def __init__(self, path, code):
        self.paths = [{"loc": path, "type": code}]
        super().__init__(code)


def validate_citations(brief, sources, *, domain=False):
    allowed = {s["id"] for s in sources}
    for i, section in enumerate(brief.sections):
        for j, claim in enumerate(section.claims):
            path = ["sections", i, "claims", j, "source_ids"]
            if not set(claim.source_ids) <= allowed:
                raise CitationError(path, "unknown_source_ids")
            if claim.kind == "fact" and not claim.source_ids:
                raise CitationError(path, "uncited_fact")
    for i, choice in enumerate(brief.domains):
        if not set(choice.source_ids) <= allowed:
            raise CitationError(["domains", i, "source_ids"], "unknown_source_ids")
    if domain and brief.domains:
        raise CitationError(["domains"], "domain_preparation_requires_empty_domains")
    if brief.confidence != "INSUFFICIENT" and not brief.sections:
        raise CitationError(["sections"], "missing_usable_sections")
    return brief.model_dump()


def brief_markdown(brief):
    lines = []
    for section in brief.get("sections", []):
        lines.append("## " + section["title"])
        for claim in section["claims"]:
            label = "Recommendation: " if claim["kind"] == "recommendation" else ""
            citations = "".join(f"[{sid}]" for sid in claim["source_ids"])
            lines.append(f"- {label}{claim['text']} {citations}".strip())
    return "\n\n".join(lines)
