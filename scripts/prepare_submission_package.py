from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "outputs" / "sumission"
PACKAGE_DIR.mkdir(parents=True, exist_ok=True)

# Clean only the package folder we manage.
for child in PACKAGE_DIR.iterdir():
    if child.is_file() or child.is_symlink():
        child.unlink()
    elif child.is_dir():
        shutil.rmtree(child)

SOURCE_FILES = [
    (ROOT / "docs" / "competition" / "first-round" / "planning" / "m2-final-answers.csv", PACKAGE_DIR / "m2-final-answers.csv"),
    (ROOT / "reports" / "final-report-vn.md", PACKAGE_DIR / "final-report-vn.md"),
    (ROOT / "reports" / "final-report-vn.tex", PACKAGE_DIR / "final-report-vn.tex"),
    (ROOT / "outputs" / "submissions" / "submission.csv", PACKAGE_DIR / "submission.csv"),
    (ROOT / "docs" / "competition" / "first-round" / "submission-package.md", PACKAGE_DIR / "submission-package.md"),
    (ROOT / "docs" / "competition" / "first-round" / "final-package-manifest.md", PACKAGE_DIR / "final-package-manifest.md"),
    (ROOT / "outputs" / "tables" / "m9_compliance_audit.csv", PACKAGE_DIR / "m9_compliance_audit.csv"),
    (ROOT / "outputs" / "tables" / "m10_blend_selection.csv", PACKAGE_DIR / "m10_blend_selection.csv"),
    (ROOT / "outputs" / "tables" / "m8_explainability_summary.csv", PACKAGE_DIR / "m8_explainability_summary.csv"),
    (ROOT / "outputs" / "tables" / "m7_model_comparison.csv", PACKAGE_DIR / "m7_model_comparison.csv"),
]

for source, target in SOURCE_FILES:
    if not source.exists():
        raise FileNotFoundError(f"Missing source file: {source}")
    shutil.copy2(source, target)

# Build the final PDF report from the Vietnamese markdown source.
md_path = ROOT / "reports" / "final-report-vn.md"
pdf_path = PACKAGE_DIR / "final-report-vn.pdf"

# Register a Unicode-capable font available on Windows.
font_path = Path("C:/Windows/Fonts/arial.ttf")
if not font_path.exists():
    raise FileNotFoundError("Arial font not found in C:/Windows/Fonts/arial.ttf")
pdfmetrics.registerFont(TTFont("Arial", str(font_path)))

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="TitleVN",
        parent=styles["Title"],
        fontName="Arial",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
)
styles.add(
    ParagraphStyle(
        name="HeadingVN1",
        parent=styles["Heading1"],
        fontName="Arial",
        fontSize=13,
        leading=16,
        spaceBefore=8,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="HeadingVN2",
        parent=styles["Heading2"],
        fontName="Arial",
        fontSize=11,
        leading=14,
        spaceBefore=6,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="BodyVN",
        parent=styles["BodyText"],
        fontName="Arial",
        fontSize=9,
        leading=11,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="BulletVN",
        parent=styles["BodyText"],
        fontName="Arial",
        fontSize=9,
        leading=11,
        leftIndent=14,
        firstLineIndent=0,
        bulletIndent=4,
        spaceAfter=2,
    )
)


def md_to_para(text: str) -> str:
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


def parse_table(lines: list[str]) -> tuple[list[list[str]], int]:
    rows = []
    consumed = 0
    for raw in lines:
        line = raw.strip()
        if not line.startswith("|"):
            break
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) >= 2 and set(parts[1].replace("-", "").strip()) == set():
            consumed += 1
            continue
        rows.append(parts)
        consumed += 1
    return rows, consumed


story = []
lines = md_path.read_text(encoding="utf-8").splitlines()
i = 0
while i < len(lines):
    line = lines[i].rstrip()
    stripped = line.strip()
    if not stripped:
        story.append(Spacer(1, 0.08 * inch))
        i += 1
        continue
    if stripped.startswith("# "):
        story.append(Paragraph(md_to_para(stripped[2:]), styles["TitleVN"]))
        i += 1
        continue
    if stripped.startswith("## "):
        story.append(Paragraph(md_to_para(stripped[3:]), styles["HeadingVN1"]))
        i += 1
        continue
    if stripped.startswith("### "):
        story.append(Paragraph(md_to_para(stripped[4:]), styles["HeadingVN2"]))
        i += 1
        continue
    if stripped.startswith("---"):
        story.append(Spacer(1, 0.05 * inch))
        i += 1
        continue
    if stripped.startswith("|"):
        table_rows, consumed = parse_table(lines[i:])
        if table_rows:
            table = Table(table_rows, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                        ("FONTNAME", (0, 0), (-1, -1), "Arial"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("LEADING", (0, 0), (-1, -1), 10),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.08 * inch))
            i += consumed
            continue
    if stripped.startswith(('- ', '* ')):
        story.append(Paragraph(md_to_para("• " + stripped[2:]), styles["BulletVN"]))
        i += 1
        continue
    story.append(Paragraph(md_to_para(stripped), styles["BodyVN"]))
    i += 1


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Arial", 8)
    canvas.drawRightString(7.7 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(pdf_path),
    pagesize=(8.27 * inch, 11.69 * inch),
    leftMargin=0.65 * inch,
    rightMargin=0.65 * inch,
    topMargin=0.6 * inch,
    bottomMargin=0.55 * inch,
)

doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)

index_path = PACKAGE_DIR / "PACKAGE_INDEX.md"
index_path.write_text(
    "\n".join(
        [
            "# Submission Package Index",
            "",
            "This folder contains the clean submission bundle for DATATHON 2026 Round 1.",
            "",
            "## Included files",
            "- `m2-final-answers.csv`",
            "- `final-report-vn.pdf`",
            "- `final-report-vn.md`",
            "- `final-report-vn.tex`",
            "- `submission.csv`",
            "- `submission-package.md`",
            "- `final-package-manifest.md`",
            "- `m9_compliance_audit.csv`",
            "- `m10_blend_selection.csv`",
            "- `m8_explainability_summary.csv`",
            "- `m7_model_comparison.csv`",
            "",
            "## Submit these externally",
            "- Upload `submission.csv` to Kaggle.",
            "- Use `final-report-vn.pdf` for the form upload.",
            "- Provide the GitHub repository link.",
            "- Attach all student ID photos.",
            "- Confirm final-round attendance.",
        ]
    ),
    encoding="utf-8",
)

print(f"Package prepared at: {PACKAGE_DIR}")
print(f"PDF report: {pdf_path}")
