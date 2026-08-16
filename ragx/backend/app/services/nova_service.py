"""
RAGX NOVA (Neural Offline Virtual Assistant) Service
Provides an integrated AI Copilot for the RAGX Platform.
Answers user queries regarding RAGX architecture, Data Quality (S_KB),
Answer Reliability (S_Ans), 5-tuple citations, hallucination detection, and system analytics.
"""
from typing import Dict, Any, List
import re

class NovaAssistant:
    def __init__(self):
        self.name = "NOVA"
        self.role = "RAGX Neural AI Copilot"
        
    def get_welcome_greeting(self) -> Dict[str, Any]:
        return {
            "greeting": "Hello! I am NOVA, your RAGX AI Copilot.",
            "message": "I am here to guide you through Data Quality Audits, Answer Reliability Evaluation, 5-Tuple Citations, and Hallucination Risk Analysis.",
            "suggested_prompts": [
                "What is RAGX?",
                "How is Answer Reliability (S_Ans) calculated?",
                "What is a 5-tuple citation?",
                "How does Hallucination Detection work?",
                "What does the Data Quality score (S_KB) represent?"
            ]
        }

    def respond(self, message: str, context_page: str = "general") -> Dict[str, Any]:
        text = message.strip().lower()
        
        # 1. What is RAGX?
        if "what is ragx" in text or "about ragx" in text or "overview" in text:
            reply = (
                "RAGX is a specialized platform for **Data Quality Analysis & Hallucination Detection in RAG Systems**. "
                "Unlike standard RAG that acts as an unverified 'black box', RAGX audits upstream knowledge base health (S_KB) "
                "and verifies downstream answer grounding (S_Ans) by extracting claims and checking them against source evidence."
            )
            category = "PLATFORM_OVERVIEW"

        # 2. How is S_Ans / Reliability calculated?
        elif "reliability" in text or "s_ans" in text or "score" in text or "formula" in text:
            reply = (
                "Answer Reliability (S_Ans) is computed using a weighted composite formula:\n\n"
                "• **Claim Support Score (S_supp - 50%):** Percentage of extracted claims verified as SUPPORTED.\n"
                "• **Citation Coverage (S_cov - 25%):** Percentage of claims trace-mapped to 5-tuple citations.\n"
                "• **Retrieval Similarity (S_sim - 25%):** Mean cosine similarity of top retrieved chunks.\n\n"
                "**Formula:** `S_Ans = 0.50*S_supp + 0.25*S_cov + 0.25*S_sim`"
            )
            category = "RELIABILITY_METHODOLOGY"

        # 3. 5-Tuple Citations
        elif "5-tuple" in text or "tuple" in text or "citation" in text or "traceable" in text:
            reply = (
                "A **5-Tuple Citation** provides cryptographic-like traceability for every claim. It maps a statement to:\n\n"
                "1. `source_file`: Original PDF filename\n"
                "2. `page_number`: Exact page number\n"
                "3. `chunk_id`: Unique ChromaDB chunk identifier\n"
                "4. `evidence_snippet`: Source context text snippet\n"
                "5. `similarity_score`: Dense vector embedding similarity score"
            )
            category = "CITATION_TRACEABILITY"

        # 4. Hallucination Detection
        elif "hallucination" in text or "unsupported" in text or "contradicted" in text:
            reply = (
                "RAGX detects hallucinations using a 2-stage verification engine:\n\n"
                "1. **Semantic Embedding Check:** Uses SentenceTransformers (`all-MiniLM-L6-v2`) to compare claim embeddings against evidence. Similarity < 0.70 flags an **UNSUPPORTED** claim.\n"
                "2. **Numeric Disparity Regex:** Compares numbers/percentages. If numbers in the claim are missing from evidence at similarity ≥ 0.60, it flags a **CONTRADICTED** (numeric hallucination) claim."
            )
            category = "HALLUCINATION_DETECTION"

        # 5. Data Quality S_KB
        elif "data quality" in text or "s_kb" in text or "audit" in text:
            reply = (
                "Data Quality Audit evaluates the health of your uploaded PDF knowledge base before retrieval occurs. "
                "It calculates **S_KB** by penalizing unextractable text pages, chunk redundancies, high semantic overlap, and knowledge conflicts."
            )
            category = "DATA_QUALITY_AUDIT"

        # 6. Analytics
        elif "analytics" in text or "history" in text or "dashboard" in text:
            reply = (
                "The Analytics page aggregates persistent evaluation logs from `evaluation_history.json`. "
                "It tracks Total Runs, Average S_Ans, Failure Category Breakdown, and Hallucination Risk Distribution over time."
            )
            category = "ANALYTICS"

        # General / Fallback Help
        else:
            reply = (
                f"I am NOVA, your RAGX assistant! You are currently on the **{context_page.upper()}** view. "
                "Ask me anything about RAGX architecture, how to run evaluations, understanding S_Ans scores, or detecting hallucinations!"
            )
            category = "GENERAL_ASSISTANCE"

        return {
            "query": message,
            "response": reply,
            "category": category,
            "assistant_name": self.name
        }

nova_assistant = NovaAssistant()
