# RAGX — Data Quality & Hallucination Detection Engine for RAG Systems

![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![React](https://img.shields.io/badge/React-18.0-cyan.svg)
![ChromaDB](https://img.shields.io/badge/ChromaDB-VectorStore-orange.svg)
![License](https://img.shields.io/badge/License-MIT-purple.svg)
![Tests](https://img.shields.io/badge/Tests-100%25%20Passing-brightgreen.svg)

**RAGX** is an advanced AI engineering platform designed to solve the two core vulnerabilities of Retrieval-Augmented Generation (RAG) systems:
1. **Upstream Knowledge Base Data Quality Degradation ($S_{\text{KB}}$)**
2. **Downstream Factual Hallucinations & Numerical Disparities ($S_{\text{Ans}}$)**

---

## 🌟 Key Features

- **Upstream Data Quality Auditor ($S_{\text{KB}}$):** Audits uploaded PDFs for unextractable text pages, chunk redundancies, high semantic overlap, and knowledge conflicts.
- **Active Document Registry & PDF Viewer:** In-web PDF viewer with soft delete (trash filtering), document restoration, and hard delete purging.
- **Downstream Answer Reliability Evaluator ($S_{\text{Ans}}$):** Decomposes synthesized answers into atomic factual claims, computes sentence-transformer embeddings (`all-MiniLM-L6-v2`), and verifies evidence alignment.
- **Numeric Disparity Regex Checker:** Detects numerical and percentage discrepancies between claims and evidence chunks.
- **5-Tuple Citation Traceability:** Links every claim to `(source_file, page_number, chunk_id, evidence_snippet, similarity_score)`.
- **NOVA AI Copilot Assistant:** Interactive floating AI Assistant providing context-aware platform guidance, scoring math explanations, and system Q&A.
- **Executive Analytics Dashboard:** Logs evaluation runs to disk (`evaluation_history.json`) and calculates real-time reliability metrics and risk distributions.

---

## 🏗️ System Architecture

```
User Question
     │
     ▼
FastAPI Router (/api/evaluator/query-and-evaluate)
     │
     ▼
RagEngine Hybrid Retrieval (ChromaDB Vector + BM25 Keyword Search)
     │
     ▼
Context Construction & Synthesizer Answer Generation
     │
     ▼
AnswerEvaluator Pipeline:
  ├─ ClaimExtractor (Atomic Sentences)
  ├─ EvidenceMatcher (Cosine Sim + Regex Numeric Check)
  ├─ FullKBRetrievalOracle (Top-50 KB Oracle Audit)
  └─ FailureClassifier (Categorizes Failure Type)
     │
     ▼
Scoring & Citation Mapping (S_Ans Composite Score + 5-Tuple Traceability Links)
     │
     ▼
React Frontend UI & NOVA AI Assistant Display
```

---

## 📐 Scoring Methodology

Composite Answer Reliability ($S_{\text{Ans}}$) is computed as:

$$\mathbf{S_{\text{Ans}} = 0.50 \cdot S_{\text{supp}} + 0.25 \cdot S_{\text{cov}} + 0.25 \cdot S_{\text{sim}}}$$

- **$S_{\text{supp}}$ (50%):** Claim Support Sub-Score (Percentage of claims verified as `SUPPORTED`).
- **$S_{\text{cov}}$ (25%):** Citation Coverage Sub-Score (Percentage of claims mapped to 5-tuples).
- **$S_{\text{sim}}$ (25%):** Mean Cosine Similarity of retrieved context chunks.

---

## 🚀 Quick Start Guide

### 1. Clone Repository
```bash
git clone https://github.com/chandusrchandusr5-droid/RagX.git
cd RagX
```

### 2. Start Backend FastAPI Server
```powershell
cd ragx/backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3. Start Frontend React Server
```powershell
cd ragx/frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your web browser.

---

## 🧪 Automated Test Suite

Run the full automated regression test suite:
```powershell
cd ragx/backend
python -u test_lifecycle_and_viewer.py
python -u test_phase2_quality.py
python -u test_phase3_evaluator.py
python -u test_phase3_analytics_persistence.py
python -u test_heading_truncation_fix.py
python -u test_nova_assistant.py
```

---

## 📄 Project Documentation & PDF Guide

- **Complete Markdown Documentation:** [`ragx/docs/ragx_complete_project_documentation.md`](ragx/docs/ragx_complete_project_documentation.md)
- **Publication-Quality PDF Guide:** [`ragx/docs/RAGX_Complete_Project_Documentation.pdf`](ragx/docs/RAGX_Complete_Project_Documentation.pdf)

---

## 📜 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.
