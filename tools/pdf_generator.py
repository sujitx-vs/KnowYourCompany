import os
import re
import html
import uuid

from reportlab.lib import colors
from reportlab.lib.enums import (
    TA_CENTER,
    TA_LEFT
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)
from reportlab.lib.units import mm

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    ListFlowable,
    ListItem,
    HRFlowable,
    Table,
    TableStyle
)


# ============================================================
# DESIGN COLORS
# ============================================================

PRIMARY_COLOR = colors.HexColor("#1E3A5F")
SECONDARY_COLOR = colors.HexColor("#2F6690")
ACCENT_COLOR = colors.HexColor("#3A7CA5")

TEXT_COLOR = colors.HexColor("#252525")
MUTED_TEXT_COLOR = colors.HexColor("#6B7280")

LIGHT_BACKGROUND = colors.HexColor("#F4F7FA")
BORDER_COLOR = colors.HexColor("#D9E2EC")


# ============================================================
# FILE NAME HELPER
# ============================================================

def clean_filename(name):
    """
    Convert company name into a safe PDF filename.
    """

    name = name.strip().lower()

    name = re.sub(
        r"[^a-z0-9]+",
        "-",
        name
    )

    return name.strip("-")


# ============================================================
# FORMAT MARKDOWN INLINE TEXT
# ============================================================

def format_text(text):
    """
    Convert simple Markdown formatting into
    ReportLab Paragraph markup.

    Supported:

    **bold**
    *italic*
    `inline code`
    [link text](https://example.com)
    """

    if not text:
        return ""

    # Escape HTML-sensitive characters first.
    text = html.escape(
        str(text)
    )

    # --------------------------------------------------------
    # Markdown links
    # --------------------------------------------------------

    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^\)]+)\)",
        r'<a href="\2" color="#2F6690"><u>\1</u></a>',
        text
    )

    # --------------------------------------------------------
    # Bold
    # --------------------------------------------------------

    text = re.sub(
        r"\*\*(.+?)\*\*",
        r"<b>\1</b>",
        text
    )

    # --------------------------------------------------------
    # Italic
    # --------------------------------------------------------

    text = re.sub(
        r"(?<!\*)\*([^*]+?)\*(?!\*)",
        r"<i>\1</i>",
        text
    )

    # --------------------------------------------------------
    # Inline code
    # --------------------------------------------------------

    text = re.sub(
        r"`([^`]+?)`",
        r'<font name="Courier">\1</font>',
        text
    )

    return text


# ============================================================
# REMOVE DUPLICATE REPORT TITLE
# ============================================================

def remove_leading_title(text):
    """
    The Gemini report already normally begins with:

    # Company - Placement Preparation Report

    Since the PDF now has its own cover page,
    remove that first Markdown title.
    """

    if not text:
        return ""

    lines = text.splitlines()

    while lines and not lines[0].strip():
        lines.pop(0)

    if lines and lines[0].strip().startswith("# "):
        lines.pop(0)

    return "\n".join(lines).strip()


# ============================================================
# COVER PAGE
# ============================================================

def add_cover_page(
    story,
    company_name,
    selected_domain,
    styles
):
    """
    Create the first page of the PDF.
    """

    story.append(
        Spacer(
            1,
            42 * mm
        )
    )

    story.append(
        Paragraph(
            format_text(
                company_name.upper()
            ),
            styles["CoverCompany"]
        )
    )

    story.append(
        Spacer(
            1,
            6 * mm
        )
    )

    story.append(
        HRFlowable(
            width="38%",
            thickness=2,
            color=ACCENT_COLOR,
            spaceBefore=4,
            spaceAfter=14,
            hAlign="CENTER"
        )
    )

    story.append(
        Paragraph(
            "Placement Preparation Report",
            styles["CoverTitle"]
        )
    )

    story.append(
        Spacer(
            1,
            7 * mm
        )
    )

    story.append(
        Paragraph(
            "Company research, domain analysis and "
            "campus placement preparation",
            styles["CoverSubtitle"]
        )
    )

    if selected_domain:

        story.append(
            Spacer(
                1,
                15 * mm
            )
        )

        domain_box = Table(
            [
                [
                    Paragraph(
                        "<b>Selected Domain</b>",
                        styles["DomainBoxLabel"]
                    )
                ],
                [
                    Paragraph(
                        format_text(
                            selected_domain
                        ),
                        styles["DomainBoxValue"]
                    )
                ]
            ],
            colWidths=[
                120 * mm
            ]
        )

        domain_box.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        LIGHT_BACKGROUND
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.7,
                        BORDER_COLOR
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        12
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        12
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        8
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        8
                    )
                ]
            )
        )

        story.append(
            domain_box
        )

    story.append(
        Spacer(
            1,
            30 * mm
        )
    )

    story.append(
        Paragraph(
            "Generated by KnowYourCompany",
            styles["GeneratedBy"]
        )
    )

    story.append(
        PageBreak()
    )


# ============================================================
# PAGE FOOTER
# ============================================================

def add_page_footer(
    canvas,
    doc
):
    """
    Footer used on normal pages.
    """

    canvas.saveState()

    page_number = canvas.getPageNumber()

    page_width = A4[0]

    # --------------------------------------------------------
    # Footer separator
    # --------------------------------------------------------

    canvas.setStrokeColor(
        BORDER_COLOR
    )

    canvas.setLineWidth(
        0.5
    )

    canvas.line(
        20 * mm,
        16 * mm,
        page_width - 20 * mm,
        16 * mm
    )

    # --------------------------------------------------------
    # Application name
    # --------------------------------------------------------

    canvas.setFillColor(
        MUTED_TEXT_COLOR
    )

    canvas.setFont(
        "Helvetica",
        8
    )

    canvas.drawString(
        20 * mm,
        10 * mm,
        "KnowYourCompany"
    )

    # --------------------------------------------------------
    # Page number
    # --------------------------------------------------------

    canvas.drawRightString(
        page_width - 20 * mm,
        10 * mm,
        f"Page {page_number}"
    )

    canvas.restoreState()


# ============================================================
# COVER PAGE FOOTER
# ============================================================

def add_cover_footer(
    canvas,
    doc
):
    """
    Minimal footer for first page.
    """

    canvas.saveState()

    canvas.setFillColor(
        MUTED_TEXT_COLOR
    )

    canvas.setFont(
        "Helvetica",
        8
    )

    canvas.drawCentredString(
        A4[0] / 2,
        10 * mm,
        "KnowYourCompany"
    )

    canvas.restoreState()


# ============================================================
# MARKDOWN CONTENT PARSER
# ============================================================

def add_markdown_content(
    story,
    text,
    styles
):
    """
    Convert Gemini Markdown-like text into
    styled ReportLab elements.

    Supports:

    # Heading
    ## Heading
    ### Heading

    - Bullet
    * Bullet

    1. Numbered item

    **Bold**
    *Italic*
    `Code`
    """

    if not text:
        return

    lines = text.splitlines()

    bullet_items = []
    numbered_items = []


    # ========================================================
    # FLUSH BULLET LIST
    # ========================================================

    def flush_bullets():

        nonlocal bullet_items

        if not bullet_items:
            return

        story.append(
            ListFlowable(
                bullet_items,
                bulletType="bullet",
                start="circle",
                leftIndent=18,
                bulletFontName="Helvetica",
                bulletFontSize=7,
                bulletColor=SECONDARY_COLOR,
                spaceAfter=7
            )
        )

        bullet_items = []


    # ========================================================
    # FLUSH NUMBERED LIST
    # ========================================================

    def flush_numbers():

        nonlocal numbered_items

        if not numbered_items:
            return

        story.append(
            ListFlowable(
                numbered_items,
                bulletType="1",
                start="1",
                leftIndent=22,
                bulletFontName="Helvetica-Bold",
                bulletFontSize=9,
                bulletColor=SECONDARY_COLOR,
                spaceAfter=8
            )
        )

        numbered_items = []


    # ========================================================
    # PROCESS LINES
    # ========================================================

    for raw_line in lines:

        line = raw_line.strip()

        # ----------------------------------------------------
        # Empty line
        # ----------------------------------------------------

        if not line:

            flush_bullets()
            flush_numbers()

            story.append(
                Spacer(
                    1,
                    3
                )
            )

            continue


        # ----------------------------------------------------
        # Horizontal separator
        # ----------------------------------------------------

        if line in [
            "---",
            "***",
            "___"
        ]:

            flush_bullets()
            flush_numbers()

            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=BORDER_COLOR,
                    spaceBefore=6,
                    spaceAfter=10
                )
            )

            continue


        # ====================================================
        # HEADING LEVEL 3
        # ====================================================

        if line.startswith("### "):

            flush_bullets()
            flush_numbers()

            story.append(
                Paragraph(
                    format_text(
                        line[4:]
                    ),
                    styles["Heading3"]
                )
            )

            continue


        # ====================================================
        # HEADING LEVEL 2
        # ====================================================

        if line.startswith("## "):

            flush_bullets()
            flush_numbers()

            story.append(
                Spacer(
                    1,
                    4
                )
            )

            story.append(
                Paragraph(
                    format_text(
                        line[3:]
                    ),
                    styles["Heading2"]
                )
            )

            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.7,
                    color=BORDER_COLOR,
                    spaceBefore=2,
                    spaceAfter=8
                )
            )

            continue


        # ====================================================
        # HEADING LEVEL 1
        # ====================================================

        if line.startswith("# "):

            flush_bullets()
            flush_numbers()

            story.append(
                Paragraph(
                    format_text(
                        line[2:]
                    ),
                    styles["ReportTitle"]
                )
            )

            story.append(
                Spacer(
                    1,
                    6
                )
            )

            continue


        # ====================================================
        # BULLETS
        # ====================================================

        if (
            line.startswith("- ")
            or line.startswith("* ")
        ):

            flush_numbers()

            bullet_text = line[2:].strip()

            bullet_items.append(
                ListItem(
                    Paragraph(
                        format_text(
                            bullet_text
                        ),
                        styles["ListBody"]
                    ),
                    leftIndent=5
                )
            )

            continue


        # ====================================================
        # NUMBERED LIST
        # ====================================================

        numbered_match = re.match(
            r"^\d+\.\s+(.*)",
            line
        )

        if numbered_match:

            flush_bullets()

            item_text = (
                numbered_match
                .group(1)
                .strip()
            )

            numbered_items.append(
                ListItem(
                    Paragraph(
                        format_text(
                            item_text
                        ),
                        styles["ListBody"]
                    ),
                    leftIndent=5
                )
            )

            continue


        # ====================================================
        # NORMAL PARAGRAPH
        # ====================================================

        flush_bullets()
        flush_numbers()

        story.append(
            Paragraph(
                format_text(
                    line
                ),
                styles["Body"]
            )
        )


    # ========================================================
    # FLUSH ANY REMAINING LIST ITEMS
    # ========================================================

    flush_bullets()
    flush_numbers()


# ============================================================
# GENERATE PDF
# ============================================================

def create_placement_pdf(
    company_name,
    report,
    selected_domain="",
    domain_analysis="",
    output_dir="outputs",
    report_id=None
):
    """
    Generate the final placement preparation PDF.

    This function signature remains compatible
    with graph.py.
    """

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    os.makedirs(
        output_dir,
        exist_ok=True
    )


    # --------------------------------------------------------
    # Safe and unique filename
    # --------------------------------------------------------

    safe_company = clean_filename(
        company_name
    )

    if not report_id:
        report_id = uuid.uuid4().hex[:8]

    filename = (
        f"{safe_company}-{report_id}-"
        f"placement-report.pdf"
    )

    filepath = os.path.join(
        output_dir,
        filename
    )


    # ========================================================
    # DOCUMENT
    # ========================================================

    document = SimpleDocTemplate(
        filepath,

        pagesize=A4,

        rightMargin=20 * mm,
        leftMargin=20 * mm,

        topMargin=18 * mm,
        bottomMargin=22 * mm,

        title=(
            f"{company_name} "
            f"Placement Preparation Report"
        ),

        author="KnowYourCompany",

        subject=(
            "Campus Placement Preparation Report"
        )
    )


    # ========================================================
    # BASE STYLES
    # ========================================================

    sample_styles = (
        getSampleStyleSheet()
    )


    # ========================================================
    # COVER COMPANY NAME
    # ========================================================

    cover_company = ParagraphStyle(
        "CoverCompany",

        parent=sample_styles["Title"],

        fontName="Helvetica-Bold",

        fontSize=24,

        leading=30,

        alignment=TA_CENTER,

        textColor=PRIMARY_COLOR,

        spaceAfter=4
    )


    # ========================================================
    # COVER TITLE
    # ========================================================

    cover_title = ParagraphStyle(
        "CoverTitle",

        parent=sample_styles["Title"],

        fontName="Helvetica-Bold",

        fontSize=18,

        leading=23,

        alignment=TA_CENTER,

        textColor=TEXT_COLOR,

        spaceAfter=6
    )


    # ========================================================
    # COVER SUBTITLE
    # ========================================================

    cover_subtitle = ParagraphStyle(
        "CoverSubtitle",

        parent=sample_styles[
            "BodyText"
        ],

        fontName="Helvetica",

        fontSize=10.5,

        leading=16,

        alignment=TA_CENTER,

        textColor=MUTED_TEXT_COLOR
    )


    # ========================================================
    # GENERATED BY
    # ========================================================

    generated_by = ParagraphStyle(
        "GeneratedBy",

        parent=sample_styles[
            "BodyText"
        ],

        fontName="Helvetica",

        fontSize=9,

        leading=13,

        alignment=TA_CENTER,

        textColor=MUTED_TEXT_COLOR
    )


    # ========================================================
    # REPORT TITLE
    # ========================================================

    report_title = ParagraphStyle(
        "ReportTitle",

        parent=sample_styles[
            "Title"
        ],

        fontName="Helvetica-Bold",

        fontSize=19,

        leading=24,

        alignment=TA_LEFT,

        textColor=PRIMARY_COLOR,

        spaceBefore=8,

        spaceAfter=12
    )


    # ========================================================
    # HEADING 2
    # ========================================================

    heading2 = ParagraphStyle(
        "CustomHeading2",

        parent=sample_styles[
            "Heading2"
        ],

        fontName="Helvetica-Bold",

        fontSize=14,

        leading=19,

        textColor=PRIMARY_COLOR,

        spaceBefore=13,

        spaceAfter=5,

        keepWithNext=True
    )


    # ========================================================
    # HEADING 3
    # ========================================================

    heading3 = ParagraphStyle(
        "CustomHeading3",

        parent=sample_styles[
            "Heading3"
        ],

        fontName="Helvetica-Bold",

        fontSize=11.5,

        leading=16,

        textColor=SECONDARY_COLOR,

        spaceBefore=10,

        spaceAfter=5,

        keepWithNext=True
    )


    # ========================================================
    # BODY
    # ========================================================

    body = ParagraphStyle(
        "Body",

        parent=sample_styles[
            "BodyText"
        ],

        fontName="Helvetica",

        fontSize=10,

        leading=15.5,

        alignment=TA_LEFT,

        textColor=TEXT_COLOR,

        spaceAfter=7
    )


    # ========================================================
    # LIST BODY
    # ========================================================

    list_body = ParagraphStyle(
        "ListBody",

        parent=body,

        fontSize=9.8,

        leading=14.5,

        spaceAfter=3
    )


    # ========================================================
    # PART TITLE
    # ========================================================

    part_title = ParagraphStyle(
        "PartTitle",

        parent=sample_styles[
            "Heading1"
        ],

        fontName="Helvetica-Bold",

        fontSize=17,

        leading=22,

        textColor=PRIMARY_COLOR,

        spaceBefore=4,

        spaceAfter=5
    )


    # ========================================================
    # PART SUBTITLE
    # ========================================================

    part_subtitle = ParagraphStyle(
        "PartSubtitle",

        parent=body,

        fontName="Helvetica",

        fontSize=10,

        leading=15,

        textColor=MUTED_TEXT_COLOR,

        spaceAfter=12
    )


    # ========================================================
    # DOMAIN BOX LABEL
    # ========================================================

    domain_box_label = ParagraphStyle(
        "DomainBoxLabel",

        parent=body,

        fontSize=9,

        textColor=MUTED_TEXT_COLOR,

        spaceAfter=0
    )


    # ========================================================
    # DOMAIN BOX VALUE
    # ========================================================

    domain_box_value = ParagraphStyle(
        "DomainBoxValue",

        parent=body,

        fontName="Helvetica-Bold",

        fontSize=11,

        leading=15,

        textColor=PRIMARY_COLOR,

        spaceAfter=0
    )


    # ========================================================
    # STYLE DICTIONARY
    # ========================================================

    styles = {

        "CoverCompany":
            cover_company,

        "CoverTitle":
            cover_title,

        "CoverSubtitle":
            cover_subtitle,

        "GeneratedBy":
            generated_by,

        "ReportTitle":
            report_title,

        "Heading2":
            heading2,

        "Heading3":
            heading3,

        "Body":
            body,

        "ListBody":
            list_body,

        "PartTitle":
            part_title,

        "PartSubtitle":
            part_subtitle,

        "DomainBoxLabel":
            domain_box_label,

        "DomainBoxValue":
            domain_box_value
    }


    # ========================================================
    # BUILD DOCUMENT
    # ========================================================

    story = []


    # ========================================================
    # COVER PAGE
    # ========================================================

    add_cover_page(
        story=story,

        company_name=
            company_name,

        selected_domain=
            selected_domain,

        styles=
            styles
    )


    # ========================================================
    # PART A
    # ========================================================

    story.append(
        Paragraph(
            "PART A",
            styles["PartTitle"]
        )
    )

    story.append(
        Paragraph(
            "Company Research & Placement Preparation",
            styles["PartSubtitle"]
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=ACCENT_COLOR,
            spaceBefore=2,
            spaceAfter=14
        )
    )


    cleaned_report = (
        remove_leading_title(
            report
        )
    )


    add_markdown_content(
        story,
        cleaned_report,
        styles
    )


    # ========================================================
    # PART B
    # ========================================================

    if domain_analysis:

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                "PART B",
                styles["PartTitle"]
            )
        )

        story.append(
            Paragraph(
                "Selected Domain Analysis",
                styles["PartSubtitle"]
            )
        )

        story.append(
            HRFlowable(
                width="100%",
                thickness=1.5,
                color=ACCENT_COLOR,
                spaceBefore=2,
                spaceAfter=14
            )
        )


        # ----------------------------------------------------
        # Selected domain box
        # ----------------------------------------------------

        if selected_domain:

            domain_box = Table(
                [
                    [
                        Paragraph(
                            "<b>Selected Domain</b>",
                            styles[
                                "DomainBoxLabel"
                            ]
                        )
                    ],
                    [
                        Paragraph(
                            format_text(
                                selected_domain
                            ),
                            styles[
                                "DomainBoxValue"
                            ]
                        )
                    ]
                ],

                colWidths=[
                    160 * mm
                ]
            )


            domain_box.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, -1),
                            LIGHT_BACKGROUND
                        ),

                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.8,
                            BORDER_COLOR
                        ),

                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            12
                        ),

                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            12
                        ),

                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            8
                        ),

                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            8
                        )
                    ]
                )
            )


            story.append(
                domain_box
            )

            story.append(
                Spacer(
                    1,
                    12
                )
            )


        # ----------------------------------------------------
        # Domain analysis
        # ----------------------------------------------------

        add_markdown_content(
            story,
            domain_analysis,
            styles
        )


    # ========================================================
    # GENERATE PDF
    # ========================================================

    document.build(

        story,

        onFirstPage=
            add_cover_footer,

        onLaterPages=
            add_page_footer
    )


    return filepath