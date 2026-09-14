"""Render the same cited, structured dossier that the browser displays."""
import html
import os
from pathlib import Path
import re
import uuid
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether

INK = colors.HexColor("#20251F")
GREEN = colors.HexColor("#234D3C")

def text(value):
    return html.escape(str(value))

def fonts():
    candidates = [
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
        (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
    ]
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            if "Dossier" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("Dossier", str(regular)))
                pdfmetrics.registerFont(TTFont("DossierBold", str(bold)))
            return "Dossier", "DossierBold"
    return "Helvetica", "Helvetica-Bold"

def create_dossier_pdf(state, report_id=None, output_dir=None):
    root = Path(output_dir or os.getenv("REPORT_DIR", "outputs")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    filename = re.sub(r"[^a-zA-Z0-9-]", "", report_id or uuid.uuid4().hex) + "-dossier.pdf"
    path = root / filename
    normal, bold = fonts()
    styles = {
        "label": ParagraphStyle("label", fontName=bold, fontSize=9, leading=13, textColor=GREEN, spaceAfter=10),
        "title": ParagraphStyle("title", fontName=bold, fontSize=27, leading=32, textColor=INK, spaceAfter=14),
        "heading": ParagraphStyle("heading", fontName=bold, fontSize=13, leading=18, textColor=GREEN, spaceBefore=15, spaceAfter=8, keepWithNext=True),
        "body": ParagraphStyle("body", fontName=normal, fontSize=10, leading=15, textColor=INK, spaceAfter=8),
        "source": ParagraphStyle("source", fontName=normal, fontSize=8, leading=12, textColor=INK, spaceAfter=9, splitLongWords=True),
    }
    story = [Paragraph("KNOWYOURCOMPANY / RESEARCH DOSSIER", styles["label"]),
             Paragraph(text(state["company_name"]), styles["title"]),
             Paragraph(text(state.get("selected_domain") or "Company brief"), styles["body"]),
             Paragraph("Researched: " + text(state.get("researched_at", "Date unavailable")[:10]), styles["source"]),
             HRFlowable(width="100%", thickness=1, color=GREEN), Spacer(1, 6*mm)]
    for label, brief in [("01 / COMPANY BRIEF", state.get("company_brief")), ("02 / PREPARATION BRIEF", state.get("domain_brief"))]:
        if not brief:
            continue
        story.append(Paragraph(label, styles["heading"]))
        story.append(Paragraph("Evidence: " + text(brief["confidence"]) + ". " + text(brief["summary"]), styles["body"]))
        for section in brief["sections"]:
            story.append(Paragraph(text(section["title"]), styles["heading"]))
            for claim in section["claims"]:
                prefix = "Recommendation: " if claim["kind"] == "recommendation" else ""
                citations = " ".join(f'<a href="#source-{text(sid)}" color="#234D3C">[{text(sid)}]</a>' for sid in claim["source_ids"])
                story.append(Paragraph(text(prefix + claim["text"]) + " " + citations, styles["body"]))
    story.append(Paragraph("03 / SOURCE REGISTER", styles["heading"]))
    for source in state.get("search_results", []) + state.get("domain_search_results", []):
        sid, url = text(source["id"]), text(source["url"])
        story.append(Paragraph(f'<a name="source-{sid}"/>[{sid}] {text(source["title"])}<br/><a href="{url}" color="#234D3C">{url}</a><br/>Retrieved: {text(source.get("retrieved_at", "")[:10])}', styles["source"]))
    story.append(Paragraph("Company facts are linked to public evidence. Preparation suggestions are recommendations, not confirmed interview questions. Verify current hiring requirements with the company.", styles["source"]))
    def footer(canvas, doc):
        canvas.setStrokeColor(colors.HexColor("#D8D7CD"))
        canvas.line(20*mm, 17*mm, 190*mm, 17*mm)
        canvas.setFont(normal, 8)
        canvas.setFillColor(INK)
        canvas.drawString(20*mm, 12*mm, "KnowYourCompany")
        canvas.drawRightString(190*mm, 12*mm, str(doc.page))
    SimpleDocTemplate(str(path), rightMargin=20*mm, leftMargin=20*mm,
                      topMargin=18*mm, bottomMargin=24*mm,
                      title=state["company_name"] + " / Company dossier", author="KnowYourCompany").build(story, onFirstPage=footer, onLaterPages=footer)
    return str(path)
