import sys
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

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
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "RAGX Platform — Teammate Guide & System Architecture")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Footer (all pages)
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 36, footer_text)
        self.drawString(54, 36, "CONFIDENTIAL & PROPRIETARY — RAGX TEAM")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 48, 8.5 * inch - 54, 48)
        
        self.restoreState()

def create_pdf(filename="RAGX_How_It_Works_Teammate_Guide.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#4F46E5")     # Indigo 600
    SECONDARY = colors.HexColor("#0F172A")   # Slate 900
    ACCENT = colors.HexColor("#0D9488")      # Teal 600
    TEXT_DARK = colors.HexColor("#1E293B")   # Slate 800
    BG_LIGHT = colors.HexColor("#F8FAFC")    # Slate 50
    BORDER_COLOR = colors.HexColor("#E2E8F0")

    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=PRIMARY,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#475569"),
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=SECONDARY,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=TEXT_DARK,
        spaceAfter=8
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=body_style,
        fontName='Helvetica-Oblique',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#334155")
    )

    story = []

    # -------------------------------------------------------------
    # HEADER BANNER
    # -------------------------------------------------------------
    story.append(Paragraph("RAGX System Architecture & How It Works", title_style))
    story.append(Paragraph("A Teammate's Guide to Data Quality, RAG Ingestion, and Hallucination Detection", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceBefore=0, spaceAfter=15))

    # -------------------------------------------------------------
    # SECTION 1: EXECUTIVE SUMMARY
    # -------------------------------------------------------------
    story.append(Paragraph("1. What is RAGX and Why Do We Need It?", h1_style))
    story.append(Paragraph(
        "Modern Artificial Intelligence (AI) uses Large Language Models (LLMs) to answer user questions. "
        "However, raw LLMs often suffer from a critical flaw called <b>Hallucination</b>—they generate incorrect facts with absolute confidence.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Retrieval-Augmented Generation (RAG)</b> solves part of this problem by giving the LLM internal company documents (PDFs) to read before answering. "
        "However, standard RAG systems still fail when documents contain errors or when the AI mixes up facts.",
        body_style
    ))
    story.append(Paragraph(
        "<b>RAGX is our end-to-end platform that audits document quality and continuously evaluates answer reliability before answers reach the user.</b>",
        body_style
    ))

    # Callout Box
    callout_data = [[
        Paragraph("<b>Key Takeaway for Team:</b> RAGX ensures that every AI answer is 100% traceable back to specific lines and pages in our uploaded PDFs. If an answer cannot be proven by our documents, RAGX catches and flags it immediately.", callout_style)
    ]]
    callout_table = Table(callout_data, colWidths=[7.0 * inch])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EEF2FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#C7D2FE")),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 14))

    # -------------------------------------------------------------
    # SECTION 2: THE 3-PHASE PIPELINE
    # -------------------------------------------------------------
    story.append(Paragraph("2. How RAGX Works: The 3 Core Phases", h1_style))
    story.append(Paragraph(
        "RAGX operates in three distinct, automated phases to transform raw PDFs into verified, hallucination-free answers:",
        body_style
    ))

    phase_table_data = [
        [Paragraph("<b>Phase</b>", body_style), Paragraph("<b>Name & Purpose</b>", body_style), Paragraph("<b>Key Output</b>", body_style)],
        [
            Paragraph("<b>Phase 1</b>", body_style),
            Paragraph("<b>RAG Data Ingestion & Retrieval</b><br/>Parses uploaded PDFs, converts text into mathematical vector embeddings, and stores them in ChromaDB.", body_style),
            Paragraph("Indexed Vector Chunks & Candidate Contexts", body_style)
        ],
        [
            Paragraph("<b>Phase 2</b>", body_style),
            Paragraph("<b>Data Quality Audit Engine</b><br/>Audits uploaded documents before querying. Checks text completeness, chunk diversity, and knowledge contradictions.", body_style),
            Paragraph("Health Score & Contradiction Matrix", body_style)
        ],
        [
            Paragraph("<b>Phase 3</b>", body_style),
            Paragraph("<b>Answer Reliability & Hallucination Evaluator</b><br/>Decomposes LLM answers into atomic claims, matches claims to evidence, and computes composite reliability score (S_Ans).", body_style),
            Paragraph("5-Tuple Traceability & Reliability Badge", body_style)
        ]
    ]

    phase_table = Table(phase_table_data, colWidths=[0.9 * inch, 3.8 * inch, 2.3 * inch])
    phase_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F1F5F9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(phase_table)
    story.append(Spacer(1, 14))

    # -------------------------------------------------------------
    # SECTION 3: STEP-BY-STEP DATA FLOW
    # -------------------------------------------------------------
    story.append(Paragraph("3. Step-by-Step Data Journey (From User Query to Verified Answer)", h1_style))
    
    steps = [
        ("Step 1: Document Upload & Chunking", "When a PDF (e.g. <i>2ND SEM RESULT.pdf</i>) is uploaded via the <b>Documents Tab</b>, PyMuPDF extracts text and PyTorch splits text into 500-character vector chunks."),
        ("Step 2: Vector Store Indexing", "Each chunk is embedded using the <code>all-MiniLM-L6-v2</code> neural model and indexed in ChromaDB vector database."),
        ("Step 3: User Query Submission", "When a user asks a question (e.g. <i>'What are the marks in Mathematics-II?'</i>), ChromaDB searches for top-3 semantically relevant chunks."),
        ("Step 4: Answer Synthesis", "The RAG engine builds a context prompt and synthesizes a direct answer derived strictly from the retrieved chunks."),
        ("Step 5: Claim Extraction & Matching", "Phase 3 ClaimExtractor breaks the answer into atomic factual statements (e.g., <i>'BMATS201 MATHEMATICS-II 35 11 46 F'</i>) and verifies each against source evidence."),
        ("Step 6: Reliability Scoring & Badge", "AnswerEvaluator calculates composite reliability score (S_Ans) and displays a green <b>HIGHLY_RELIABLE</b> or red <b>UNRELIABLE</b> badge.")
    ]

    for title, desc in steps:
        story.append(Paragraph(f"• <b>{title}</b>: {desc}", bullet_style))
    story.append(Spacer(1, 14))

    # -------------------------------------------------------------
    # SECTION 4: THE RELIABILITY FORMULA & 5-TUPLE TRACEABILITY
    # -------------------------------------------------------------
    story.append(Paragraph("4. How RAGX Scores Answer Reliability (S_Ans)", h1_style))
    story.append(Paragraph(
        "RAGX does not guess reliability—it uses a mathematically deterministic formula bounded between 0% and 100%:",
        body_style
    ))

    # Formula Callout
    formula_data = [[
        Paragraph("<b>S_Ans = (0.60 × Claim Support) + (0.20 × Citation Coverage) + (0.20 × Retrieval Similarity)</b>", ParagraphStyle('Formula', parent=body_style, fontName='Helvetica-Bold', fontSize=10.5, textColor=PRIMARY, alignment=1))
    ]]
    formula_table = Table(formula_data, colWidths=[7.0 * inch])
    formula_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 1, PRIMARY),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    story.append(formula_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Understanding 5-Tuple Traceability:</b>", h2_style))
    story.append(Paragraph(
        "Every claim generated by RAGX is linked to a strict 5-tuple proof chain:",
        body_style
    ))
    story.append(Paragraph("<code>Claim Text  ──>  Evidence Text  ──>  Chunk ID  ──>  Document Name  ──>  Page Number</code>", ParagraphStyle('CodeLine', parent=body_style, fontName='Courier-Bold', fontSize=9, textColor=PRIMARY, leftIndent=15)))
    story.append(Spacer(1, 10))

    # -------------------------------------------------------------
    # SECTION 5: TEAMMATE QUICK UI GUIDE
    # -------------------------------------------------------------
    story.append(Paragraph("5. Teammate Guide: Using the RAGX Web App", h1_style))

    ui_guide_data = [
        [Paragraph("<b>Tab Name</b>", body_style), Paragraph("<b>What Teammates Can Do Here</b>", body_style)],
        [
            Paragraph("📁 <b>Documents</b>", body_style),
            Paragraph("Upload new PDFs, view indexed document status, preview PDFs directly in-web, and soft-delete/restore documents from trash.", body_style)
        ],
        [
            Paragraph("⚙️ <b>Data Quality</b>", body_style),
            Paragraph("Audit uploaded PDFs for text extraction completeness, chunk diversity, and knowledge contradictions before running queries.", body_style)
        ],
        [
            Paragraph("💬 <b>RAG Chat</b>", body_style),
            Paragraph("Ask questions about company documents and receive instant answers backed by document chunk references.", body_style)
        ],
        [
            Paragraph("🛡️ <b>RAGX Evaluator</b>", body_style),
            Paragraph("Run in-depth reliability reports on any query. View claim-by-claim breakdown, support status, and 5-tuple citation proofs.", body_style)
        ],
        [
            Paragraph("📊 <b>Analytics</b>", body_style),
            Paragraph("View system-wide evaluation metrics, average reliability scores over time, and risk distribution charts.", body_style)
        ]
    ]

    ui_table = Table(ui_guide_data, colWidths=[1.8 * inch, 5.2 * inch])
    ui_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F1F5F9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(ui_table)
    story.append(Spacer(1, 15))

    # Summary Sign-off
    story.append(Paragraph("<b>Summary:</b> RAGX provides total confidence in AI answers by pairing dynamic vector retrieval with deterministic 5-tuple proof verification.", ParagraphStyle('FinalNote', parent=body_style, fontName='Helvetica-Bold', fontSize=10, textColor=SECONDARY)))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully created: {filename}")

if __name__ == "__main__":
    create_pdf()
