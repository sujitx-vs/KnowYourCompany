"""Validated public brief schema shared by the browser and PDF renderer."""
from typing import Literal
from pydantic import BaseModel, Field

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
    text: str = Field(min_length=1, max_length=1600)
    kind: Literal["fact", "recommendation", "limitation"]
    source_ids: list[str] = Field(max_length=10)


class Section(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    claims: list[Claim] = Field(min_length=1, max_length=8)


class Domain(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=500)
    source_ids: list[str] = Field(min_length=1, max_length=8)


class Brief(BaseModel):
    confidence: Confidence
    summary: str = Field(max_length=700, description="Describe evidence coverage and limitations, not uncited company facts")
    sections: list[Section] = Field(max_length=8)
    domains: list[Domain] = Field(max_length=8, description="Company brief only; empty for domain preparation")


def validate_citations(brief, sources):
    allowed = {s["id"] for s in sources}
    for section in brief.sections:
        for claim in section.claims:
            if not set(claim.source_ids) <= allowed:
                raise ValueError("The brief references unavailable evidence")
            if claim.kind == "fact" and not claim.source_ids:
                raise ValueError("A company fact has no source")
    for domain in brief.domains:
        if not set(domain.source_ids) <= allowed:
            raise ValueError("A domain references unavailable evidence")
    if brief.confidence != "INSUFFICIENT" and not brief.sections:
        raise ValueError("A usable brief must contain sections")
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
