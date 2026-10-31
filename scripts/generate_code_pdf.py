import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Preformatted
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            return  # Suppress headers/footers on title page
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#4F46E5"))
        self.drawString(54, letter[1] - 36, "PortXFolio — Quantitative Trading & Risk Platform")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawRightString(letter[0] - 54, letter[1] - 36, "COE Project Submission: Complete Source Code")

        # Top border rule
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)

        # Bottom border rule & Footer
        self.line(54, 45, letter[0] - 54, 45)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(54, 32, "Confidential — Center of Excellence (COE) Project Portfolio")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 32, page_str)
        self.restoreState()

def build_code_pdf():
    pdf_filename = PROJECT_ROOT / "PortXFolio_Complete_Source_Code.pdf"
    print(f"Generating Code Dossier at: {pdf_filename}")

    doc = SimpleDocTemplate(
        str(pdf_filename),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=28,
        leading=34,
        textColor=colors.HexColor("#1E1B4B"),
        alignment=1,
        spaceAfter=15
    )
    subtitle_style = ParagraphStyle(
        "CoverSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#4338CA"),
        alignment=1,
        spaceAfter=25
    )
    meta_style = ParagraphStyle(
        "CoverMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#334155"),
        alignment=1
    )
    heading_style = ParagraphStyle(
        "FileHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.white,
        spaceAfter=0
    )
    code_style = ParagraphStyle(
        "CodeText",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=6.5,
        leading=8.5,
        textColor=colors.HexColor("#0F172A")
    )
    toc_category_style = ParagraphStyle(
        "TOCCat",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#3730A3"),
        spaceBefore=10,
        spaceAfter=4
    )
    toc_item_style = ParagraphStyle(
        "TOCItem",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155")
    )

    story = []

    # 1. Cover Page
    story.append(Spacer(1, 100))
    story.append(Paragraph("🌐 PORTXFOLIO", title_style))
    story.append(Paragraph("Advanced Quantitative Trading, Portfolio Risk & Algorithmic Execution Platform", subtitle_style))
    story.append(Spacer(1, 20))

    meta_table_data = [
        ["Submission Track", "Center of Excellence (COE) Capstone Project"],
        ["Artifact Type", "Complete Source Code Dossier (Compiled File)"],
        ["Architecture", "FastAPI REST API + Streamlit Interactive Frontend"],
        ["Mathematical Models", "Markowitz MPT (SLSQP), HistGradientBoosting ML, Event-Driven Backtest"],
        ["Primary Languages", "Python 3.13, SQL, HTML/CSS"],
        ["Database Tier", "SQLite / SQLAlchemy 2.0 (ACID Paper Execution Engine)"],
        ["Generated For", "COE Evaluation & Project Repository Verification"],
        ["Status", "Production Grade / Streamlit Community Cloud Ready"]
    ]
    t = Table(meta_table_data, colWidths=[160, 320])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor("#1E293B")),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
    ]))
    story.append(t)
    story.append(Spacer(1, 40))
    story.append(Paragraph("Compiled Source Code Portfolio | All Rights Reserved", meta_style))
    story.append(PageBreak())

    # 2. Collect Code Files in Logical Order
    categories = [
        ("Application Entrypoint & Frontends", [
            "app.py",
            "pyproject.toml",
            "requirements.txt"
        ]),
        ("Backend Entrypoint & Core Infrastructure", [
            "backend/app/main.py",
            "backend/app/core/config.py",
            "backend/app/core/database.py",
            "backend/app/core/security.py",
            "backend/app/core/deps.py",
            "backend/app/core/logging.py"
        ]),
        ("Backend ORM Database Models", [
            "backend/app/models/__init__.py",
            "backend/app/models/user.py",
            "backend/app/models/portfolio.py",
            "backend/app/models/order.py",
            "backend/app/models/market.py",
            "backend/app/models/backtest.py",
            "backend/app/models/alert.py",
            "backend/app/models/audit.py"
        ]),
        ("Backend Pydantic V2 Schemas", [
            "backend/app/schemas/__init__.py",
            "backend/app/schemas/auth.py",
            "backend/app/schemas/portfolio.py",
            "backend/app/schemas/order.py",
            "backend/app/schemas/market.py",
            "backend/app/schemas/backtest.py",
            "backend/app/schemas/forecast.py",
            "backend/app/schemas/alert.py",
            "backend/app/schemas/report.py"
        ]),
        ("Backend Data Access Repositories", [
            "backend/app/repositories/__init__.py",
            "backend/app/repositories/user_repo.py",
            "backend/app/repositories/portfolio_repo.py",
            "backend/app/repositories/order_repo.py",
            "backend/app/repositories/market_repo.py",
            "backend/app/repositories/backtest_repo.py",
            "backend/app/repositories/alert_repo.py"
        ]),
        ("Backend Quantitative Services & Computational Engines", [
            "backend/app/services/__init__.py",
            "backend/app/services/portfolio_service.py",
            "backend/app/services/trading_engine.py",
            "backend/app/services/backtest_engine.py",
            "backend/app/services/forecast_service.py",
            "backend/app/services/market_service.py",
            "backend/app/services/alert_service.py",
            "backend/app/services/auth_service.py",
            "backend/app/services/report_service.py"
        ]),
        ("Backend REST API Routers", [
            "backend/app/routers/__init__.py",
            "backend/app/routers/auth.py",
            "backend/app/routers/portfolios.py",
            "backend/app/routers/orders.py",
            "backend/app/routers/market.py",
            "backend/app/routers/backtests.py",
            "backend/app/routers/forecasts.py",
            "backend/app/routers/alerts.py",
            "backend/app/routers/reports.py",
            "backend/app/routers/admin.py",
            "backend/app/routers/health.py"
        ]),
        ("ETL & Database Ingestion Scripts", [
            "scripts/generate_sample_data.py",
            "scripts/ingest_csv.py",
            "scripts/seed_data.py",
            "scripts/verify_e2e.py"
        ]),
        ("Automated Test Suite & Verification", [
            "tests/conftest.py",
            "tests/test_portfolio_math.py",
            "tests/test_trading_engine.py",
            "tests/test_backtester.py",
            "tests/test_forecasts.py",
            "tests/test_api_endpoints.py",
            "tests/test_auth.py"
        ]),
        ("Data Utilities & Preprocessing", [
            "src/data_pull.py",
            "src/preprocessor.py"
        ])
    ]

    # Table of Contents
    story.append(Paragraph("📋 Table of Contents & File Index", ParagraphStyle(
        "TOCTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#1E1B4B"), spaceAfter=15
    )))

    toc_rows = [["#", "Module / Source File Path", "Lines", "Size (KB)"]]
    item_counter = 1
    total_lines_all = 0
    total_bytes_all = 0

    valid_file_list = []

    for cat_title, fpaths in categories:
        for rel_path in fpaths:
            full_p = PROJECT_ROOT / rel_path
            if full_p.exists():
                text = full_p.read_text(encoding="utf-8", errors="replace")
                lines_cnt = len(text.splitlines())
                sz_kb = round(len(text.encode("utf-8")) / 1024, 1)
                total_lines_all += lines_cnt
                total_bytes_all += len(text.encode("utf-8"))
                toc_rows.append([str(item_counter), rel_path, f"{lines_cnt:,}", f"{sz_kb} KB"])
                valid_file_list.append((cat_title, rel_path, full_p, text))
                item_counter += 1

    toc_rows.append(["TOTAL", f"{len(valid_file_list)} Source Files", f"{total_lines_all:,}", f"{round(total_bytes_all/1024, 1)} KB"])

    toc_table = Table(toc_rows, colWidths=[25, 335, 70, 70])
    toc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4F46E5")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.HexColor("#F8FAFC"), colors.white]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#E2E8F0")),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # 3. Source Code Listings
    current_cat = None
    for cat_title, rel_path, full_p, text in valid_file_list:
        if cat_title != current_cat:
            current_cat = cat_title
            cat_banner = Table([[f"MODULE CLUSTER: {cat_title.upper()}"]], colWidths=[500])
            cat_banner.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#312E81")),
                ('TEXTCOLOR', (0,0), (-1,-1), colors.white),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('TOPPADDING', (0,0), (-1,-1), 5),
            ]))
            story.append(Spacer(1, 10))
            story.append(cat_banner)
            story.append(Spacer(1, 6))

        # File Header banner
        lines = text.splitlines()
        header_text = f"FILE: {rel_path}  |  {len(lines)} lines  |  {round(len(text.encode('utf-8'))/1024, 1)} KB"
        file_banner = Table([[header_text]], colWidths=[500])
        file_banner.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#4F46E5")),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.white),
            ('FONTNAME', (0,0), (-1,-1), 'Courier-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(file_banner)

        # Numbered code lines in chunks to prevent memory/flowable overflow
        formatted_code_lines = []
        for idx, line in enumerate(lines, start=1):
            # Truncate very long lines to prevent clipping
            clean_l = line.replace('\t', '    ')
            if len(clean_l) > 115:
                clean_l = clean_l[:112] + "..."
            formatted_code_lines.append(f"{idx:4d} | {clean_l}")

        # Chunk into groups of 65 lines (roughly 1 page per chunk)
        chunk_size = 65
        for i in range(0, len(formatted_code_lines), chunk_size):
            chunk = "\n".join(formatted_code_lines[i:i + chunk_size])
            story.append(Preformatted(chunk, code_style))

        story.append(Spacer(1, 12))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Source Code PDF successfully built! Size: {os.path.getsize(pdf_filename)/1024/1024:.2f} MB")

if __name__ == "__main__":
    build_code_pdf()

