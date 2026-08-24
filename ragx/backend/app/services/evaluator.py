"""
RAGX Phase 3 — RAG Answer Reliability Evaluation & Hallucination Detection Engine
Deterministic claim-level evidence matching, full-KB oracle verification, Phase 2 cross-referencing,
and transparent composite Answer Reliability Scoring.
"""
import re
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from app.core.config import settings
from app.core.vector_db import vector_db, get_shared_embedding_model
from app.services.data_quality import DataQualityService
from app.services.evaluation_history import EvaluationHistoryService

logger = logging.getLogger("ragx.evaluator")


def get_embedding_model():
    return get_shared_embedding_model()



class ClaimExtractor:
    """
    Deterministic NLP claim extractor that decomposes generated answers into individual factual claims.
    Strips intro fluff prefixes ("Based on the document...", "According to section...") while preserving claims.
    """
    @staticmethod
    def extract_claims(answer: str) -> list[dict]:
        if not answer or not answer.strip():
            return []

        # Strip common meta-prefixes
        cleaned = re.sub(
            r'^(based on (the )?(retrieved )?(document|context|file|source)s?.*?:\s*|according to section \d+:\s*)',
            '',
            answer.strip(),
            flags=re.IGNORECASE
        )

        # Split into sentences or clauses on semi-colons / periods
        raw_sentences = re.split(r'(?<=[.;])\s+', cleaned)
        claims = []
        claim_counter = 1

        for sentence in raw_sentences:
            sentence_clean = sentence.strip().rstrip(".;")
            if len(sentence_clean) >= 2:
                claims.append({
                    "claim_id": f"CLM-{claim_counter:03d}",
                    "claim_text": sentence_clean
                })
                claim_counter += 1

        # Fallback if sentence splitting produced nothing
        if not claims and len(cleaned.strip()) > 0:
            claims.append({
                "claim_id": "CLM-001",
                "claim_text": cleaned.strip()
            })

        return claims


class FullKBRetrievalOracle:
    """
    Queries the entire ChromaDB vector store (K_oracle = N) to determine if relevant evidence
    exists anywhere in the knowledge base when Top-K retrieval misses it.
    """
    @staticmethod
    def search_oracle(query: str, similarity_threshold: float = 0.50, owner_id: str = None) -> dict:

        try:
            all_chunks = vector_db.get_all_chunks(owner_id=owner_id)
            if not all_chunks or not all_chunks.get("documents"):
                return {"found": False, "best_similarity": 0.0, "best_chunk": None}

            documents = all_chunks["documents"]
            metadatas = all_chunks["metadatas"]
            embeddings = all_chunks.get("embeddings")

            if embeddings is None or len(embeddings) == 0:
                return {"found": False, "best_similarity": 0.0, "best_chunk": None}

            q_emb = np.array(vector_db.get_embedding(query))
            q_norm = q_emb / (np.linalg.norm(q_emb) + 1e-9)

            emb_matrix = np.array(embeddings)
            norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True) + 1e-9
            emb_norm = emb_matrix / norms
            v_sims = np.dot(emb_norm, q_norm)

            top_indices = np.argsort(v_sims)[-15:]
            best_sim = 0.0
            best_idx = 0

            for idx in reversed(top_indices):
                v_sim = float(v_sims[idx])
                doc = documents[idx]
                h_sim = vector_db._compute_hybrid_score(query, doc, v_sim)
                if h_sim > best_sim:
                    best_sim = h_sim
                    best_idx = idx

            if best_sim >= similarity_threshold:
                best_meta = metadatas[best_idx]
                return {
                    "found": True,
                    "best_similarity": round(best_sim, 4),
                    "best_chunk": {
                        "chunk_id": best_meta.get("chunk_id", f"chunk_{best_idx}"),
                        "document_name": best_meta.get("document_name", "Unknown"),
                        "page_number": best_meta.get("page_number", 1),
                        "text": documents[best_idx]
                    }
                }
            return {"found": False, "best_similarity": round(best_sim, 4), "best_chunk": None}

        except Exception as e:
            logger.error(f"Error executing Full-KB Oracle vector search: {e}")
            return {"found": False, "best_similarity": 0.0, "best_chunk": None}


class EvidenceMatcher:
    """
    Evaluates each claim against retrieved Top-K evidence chunks using embedding similarity and numeric verification.
    Distinguishes Question Relevance (SUPPORTED_RELEVANT vs SUPPORTED_IRRELEVANT over-generation) from Factual Support.
    Strictly verifies 5-tuple citation traceability:
    claim -> evidence_chunk -> chunk_id -> document_name -> page_number.
    """
    @staticmethod
    def match_claims_to_evidence(claims: list[dict], retrieved_chunks: list[dict], query: str = None) -> tuple[list[dict], float]:
        if not claims or not retrieved_chunks:
            return claims, 0.0

        model = get_embedding_model()
        num_pattern = re.compile(r'\b\d+(?:\.\d+)?%?\b')

        # Encode claim embeddings, chunk embeddings, and query embedding
        claim_texts = [c["claim_text"] for c in claims]
        chunk_texts = [c.get("text", "") for c in retrieved_chunks]

        claim_embs = model.encode(claim_texts, convert_to_numpy=True)
        chunk_embs = model.encode(chunk_texts, convert_to_numpy=True)

        # Normalize
        claim_norms = claim_embs / (np.linalg.norm(claim_embs, axis=1, keepdims=True) + 1e-9)
        chunk_norms = chunk_embs / (np.linalg.norm(chunk_embs, axis=1, keepdims=True) + 1e-9)

        # Query embedding for Question Relevance check
        if query:
            q_emb = np.array(vector_db.get_embedding(query))
            q_norm = q_emb / (np.linalg.norm(q_emb) + 1e-9)
            q_rel_sims = np.dot(claim_norms, q_norm)
        else:
            q_rel_sims = np.ones(len(claims))

        # Cosine similarity matrix: N_claims x N_chunks
        sim_matrix = np.dot(claim_norms, chunk_norms.T)

        matched_claims = []
        all_top_sims = []

        stopwords = {
            "a", "an", "the", "and", "or", "but", "if", "because", "as", "until", "while",
            "of", "at", "by", "for", "with", "about", "against", "between", "into", "through",
            "during", "before", "after", "above", "below", "to", "from", "up", "down", "in",
            "out", "on", "off", "over", "under", "again", "further", "then", "once", "here",
            "there", "when", "where", "why", "how", "all", "any", "both", "each", "few",
            "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own",
            "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don",
            "should", "now", "is", "am", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "having", "do", "does", "did", "doing"
        }
        q_tokens = [w.lower() for w in re.findall(r'\w+', query) if w.lower() not in stopwords] if query else []

        for i, claim in enumerate(claims):
            c_text = claim["claim_text"]
            best_chunk_idx = int(np.argmax(sim_matrix[i]))
            best_sim = float(sim_matrix[i, best_chunk_idx])

            best_chunk = retrieved_chunks[best_chunk_idx]
            ev_text = best_chunk.get("text", "")
            chunk_id = best_chunk.get("id") or best_chunk.get("chunk_id", "N/A")
            doc_name = best_chunk.get("document_name", "Unknown")
            page_num = best_chunk.get("page_number", 1)

            # Direct Substring Containment Check for exact textual evidence match
            if ":" in c_text and "page" in c_text.lower()[:30]:
                c_text_clean = c_text.split(":", 1)[1].strip()
            else:
                c_text_clean = c_text.strip()

            clean_c = re.sub(r'[^a-z0-9]', '', c_text_clean.lower())
            clean_ev = re.sub(r'[^a-z0-9]', '', ev_text.lower())

            is_substring_match = bool(clean_c and len(clean_c) >= 2 and (clean_c in clean_ev or clean_c[:30] in clean_ev))

            if is_substring_match:
                best_sim = max(best_sim, 0.90)

            all_top_sims.append(best_sim)

            # Extract numeric figures for numeric disparity check
            claim_nums = num_pattern.findall(c_text.lower())
            ev_nums = num_pattern.findall(ev_text.lower())

            # Extract significant content terms from claim and evidence (words length >= 3 not in stopwords)
            c_content_tokens = [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_]+\b', c_text_clean) if w.lower() not in stopwords and len(w) >= 3]
            ev_content_tokens = set(w.lower() for w in re.findall(r'\b[a-zA-Z0-9_]+\b', ev_text) if w.lower() not in stopwords and len(w) >= 3)

            # Extract proper nouns / capitalized entity terms from claim text
            c_entity_tokens = set(w.lower() for w in re.findall(r'\b[A-Z][a-zA-Z0-9_]+\b', c_text) if w.lower() not in stopwords and len(w) >= 3)
            missing_entity_tokens = [et for et in c_entity_tokens if et not in ev_content_tokens and not any(et.startswith(ev[:4]) or ev.startswith(et[:4]) for ev in ev_content_tokens if len(ev) >= 3)]

            matched_content_tokens = []
            missing_content_tokens = []
            for ct in c_content_tokens:
                if ct in ev_content_tokens or any(ct.startswith(et[:4]) or et.startswith(ct[:4]) or ct[:4] in et for et in ev_content_tokens if len(et) >= 3):
                    matched_content_tokens.append(ct)
                else:
                    missing_content_tokens.append(ct)

            term_coverage_ratio = (len(matched_content_tokens) / len(c_content_tokens)) if c_content_tokens else 1.0

            # Determine Factual Support Status via Generic Proposition Verification
            if claim_nums and ev_nums and not set(claim_nums).issubset(set(ev_nums)) and best_sim >= 0.50:
                support_status = "CONTRADICTED"
                disparity_detail = f"Claim mentions '{', '.join(claim_nums)}' while evidence states '{', '.join(ev_nums)}'."
            elif claim_nums and not set(claim_nums).issubset(set(ev_nums)) and not is_substring_match:
                support_status = "UNSUPPORTED"
                disparity_detail = f"Claim numeric figures '{', '.join(claim_nums)}' are not established by retrieved evidence."
            elif missing_entity_tokens and not is_substring_match:
                support_status = "UNSUPPORTED"
                disparity_detail = f"Evidence mentions related subject matter, but lacks asserted entity/concept '{missing_entity_tokens[0]}'."
            elif is_substring_match or (best_sim >= 0.60 and term_coverage_ratio >= 0.50) or (best_sim >= 0.75 and term_coverage_ratio >= 0.40):
                support_status = "SUPPORTED"
                disparity_detail = "Claim proposition is factually established by retrieved evidence snippet."
            elif best_sim >= 0.60 and term_coverage_ratio < 0.50:
                support_status = "UNSUPPORTED"
                missing_sample = ", ".join(list(dict.fromkeys(missing_content_tokens))[:4])
                disparity_detail = f"Evidence is topically related (similarity {best_sim:.2f}), but fails to establish specific claim proposition (missing key terms: {missing_sample})."
            elif best_sim >= 0.40:
                support_status = "UNSUPPORTED"
                disparity_detail = "Partial semantic overlap, but specific claim facts are absent from evidence."
            else:
                support_status = "UNSUPPORTED"
                disparity_detail = "Low semantic similarity to retrieved evidence context."

            # Determine Question Relevance & Classification Layer
            q_rel_score = float(q_rel_sims[i]) if query else 1.0
            
            # Token match check for question relevance (with stem prefix matching e.g. mark vs marks)
            c_tokens = set(w.lower() for w in re.findall(r'\w+', c_text))
            has_q_token_overlap = any(t in c_tokens or any(t.startswith(ct[:4]) or ct.startswith(t[:4]) for ct in c_tokens if len(ct) >= 3 and len(t) >= 3) for t in q_tokens) if q_tokens else True

            # Generic predicate intent check: identify if claim is a bare entity code/proper noun fragment without predicate content
            q_proper_nouns = set(w.lower() for w in re.findall(r'\w+', query) if w.lower() not in stopwords and (re.search(r'\d', w) or w.isupper() or len(w) <= 3 or len(query.strip()) <= 4)) if query else set()
            q_predicate_tokens = [w for w in q_tokens if w not in q_proper_nouns]
            c_non_entity_tokens = [w for w in c_tokens if w not in stopwords and w not in q_proper_nouns]

            q_numeric_keywords = {"mark", "marks", "score", "scores", "total", "count", "number", "percentage", "percent", "ratio", "rate", "cost", "fee", "price", "threshold", "grade", "gpa", "val", "value", "formula"}
            q_requires_numeric = any(t in q_numeric_keywords for t in q_tokens)

            # Standalone numeric figures (excluding digits embedded inside entity codes e.g. BMATS201)
            standalone_claim_nums = [n for n in claim_nums if not re.search(r'[a-zA-Z]' + re.escape(n), c_text) and not re.search(re.escape(n) + r'[a-zA-Z]', c_text)]

            is_bare_entity_claim = bool(q_proper_nouns) and (c_tokens.issubset(q_proper_nouns) or not c_non_entity_tokens) and not standalone_claim_nums and len(c_tokens) <= 3

            if support_status == "SUPPORTED":
                if is_bare_entity_claim and q_predicate_tokens:
                    relevance_classification = "SUPPORTED_IRRELEVANT"
                    disparity_detail += " Note: Claim contains only entity identifiers but fails to answer the question predicate (Entity-Only Fragment)."
                elif q_rel_score >= 0.65 or (has_q_token_overlap and q_rel_score >= 0.35) or (bool(standalone_claim_nums) and bool(q_predicate_tokens) and support_status == "SUPPORTED"):
                    relevance_classification = "SUPPORTED_RELEVANT"
                else:
                    relevance_classification = "SUPPORTED_IRRELEVANT"
                    disparity_detail += " Note: Claim exists in source but is IRRELEVANT to the user's specific question (Over-generation)."

            elif support_status == "CONTRADICTED":
                relevance_classification = "CONTRADICTED"
            else:
                relevance_classification = "UNSUPPORTED"

            # Verify strict 5-tuple citation traceability:
            # claim -> evidence_chunk -> chunk_id -> document_name -> page_number
            has_5_tuple = (
                bool(c_text) and
                bool(ev_text) and
                chunk_id != "N/A" and
                doc_name != "Unknown" and
                page_num is not None
            )

            matched_claims.append({
                "claim_id": claim["claim_id"],
                "claim_text": c_text,
                "support_status": support_status,
                "relevance_classification": relevance_classification,
                "question_relevance_score": round(q_rel_score, 4),
                "citation_traceable": has_5_tuple,
                "matched_evidence": {
                    "source_file": doc_name,
                    "page_number": page_num,
                    "chunk_id": chunk_id,
                    "evidence_snippet": ev_text[:120] + "..." if len(ev_text) > 120 else ev_text,
                    "similarity_score": round(best_sim, 4)
                },
                "disparity_detail": disparity_detail
            })

        avg_retrieval_sim = float(np.mean(all_top_sims)) if all_top_sims else 0.0
        return matched_claims, round(avg_retrieval_sim, 4)



class Phase2CrossReferencer:
    """
    Traces retrieved evidence chunks against Phase 2 Data Quality Audit issues.
    Preserves 4 Phase 2 issue fields: issue_id, issue_status, confidence, demonstrated_impact.
    Distinguishes SUSPECTED_CONFLICT_SIGNAL (warning signal) from confirmed KNOWLEDGE_CONFLICT.
    """
    @staticmethod
    def cross_reference_issues(retrieved_chunks: list[dict]) -> tuple[list[dict], bool, bool]:
        if not retrieved_chunks:
            return [], False, False

        try:
            dq_service = DataQualityService()
            audit_report = dq_service.audit_knowledge_base()
            p2_issues = audit_report.get("issues", [])

            retrieved_chunk_ids = {
                c.get("id") or c.get("chunk_id") for c in retrieved_chunks if c.get("id") or c.get("chunk_id")
            }
            retrieved_files = {
                c.get("document_name") for c in retrieved_chunks if c.get("document_name")
            }

            matched_refs = []
            has_confirmed_conflict = False
            has_suspected_conflict = False

            for issue in p2_issues:
                issue_type = issue.get("issue_type", "")
                issue_status = issue.get("issue_status", "")
                src_file = issue.get("source_file")
                rel_file = issue.get("related_file")
                c_id = issue.get("chunk_id")

                # Match by chunk_id or document_name
                is_chunk_match = c_id in retrieved_chunk_ids if c_id != "N/A" else False
                is_file_match = (src_file in retrieved_files) or (rel_file in retrieved_files)

                if is_chunk_match or is_file_match:
                    if issue_type == "SUSPECTED_CONFLICT_SIGNAL":
                        has_suspected_conflict = True
                        mapped_status = "SUSPECTED_KNOWLEDGE_CONFLICT"
                    elif issue_type == "CONFIRMED_KNOWLEDGE_CONFLICT":
                        has_confirmed_conflict = True
                        mapped_status = "KNOWLEDGE_CONFLICT"
                    else:
                        mapped_status = issue_type

                    matched_refs.append({
                        "issue_id": issue.get("issue_id"),
                        "issue_type": issue_type,
                        "issue_status": issue_status,
                        "mapped_category": mapped_status,
                        "confidence": issue.get("confidence", 0.75),
                        "source_file": src_file,
                        "page_number": issue.get("page_number", 1),
                        "chunk_id": c_id,
                        "demonstrated_impact": f"Phase 2 quality finding '{issue.get('title')}' affects retrieved evidence context."
                    })

            return matched_refs, has_confirmed_conflict, has_suspected_conflict
        except Exception as e:
            logger.error(f"Error cross-referencing Phase 2 issues: {e}")
            return [], False, False


class QuestionAspectAnalyzer:
    """
    Analyzes multi-part complex questions into distinct requested aspects/components,
    and evaluates whether the generated answer covers all requested components using
    structural clause detection and generic semantic vector embedding comparison.
    """
    @staticmethod
    def analyze_coverage(query: str, answer: str, retrieved_evidence: list[dict]) -> dict:
        if not query or not query.strip():
            return {"coverage_ratio": 1.0, "total_aspects": 1, "covered_aspects": 1, "missing_aspects": []}

        if not answer or not answer.strip():
            return {"coverage_ratio": 0.0, "total_aspects": 1, "covered_aspects": 0, "missing_aspects": [query[:60]]}

        query_text = query.strip()
        
        # Split complex questions into distinct requested aspects using structural punctuation, transition phrases, and conjunctions
        raw_clauses = re.split(r'[,;?.]|\bas well as\b|\balong with\b|\bin addition to\b|\band\b', query_text)

        # Filter out short fragments
        clauses = [c.strip() for c in raw_clauses if len(c.strip()) > 8]
        if not clauses:
            clauses = [query_text]

        model = get_embedding_model()
        ans_emb = model.encode(answer, convert_to_numpy=True)
        ans_norm = ans_emb / (np.linalg.norm(ans_emb) + 1e-9)

        clause_embs = model.encode(clauses, convert_to_numpy=True)
        clause_norms = clause_embs / (np.linalg.norm(clause_embs, axis=1, keepdims=True) + 1e-9)

        sims = np.dot(clause_norms, ans_norm)

        total_aspects = len(clauses)
        covered_count = 0
        missing_aspects = []

        ENGLISH_STOPWORDS = {
            "a", "an", "the", "and", "or", "but", "if", "because", "as", "until", "while",
            "of", "at", "by", "for", "with", "about", "against", "between", "into", "through",
            "during", "before", "after", "above", "below", "to", "from", "up", "down", "in",
            "out", "on", "off", "over", "under", "again", "further", "then", "once", "here",
            "there", "when", "where", "why", "how", "all", "any", "both", "each", "few",
            "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own",
            "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don",
            "should", "now", "is", "am", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "having", "do", "does", "did", "doing"
        }
        core_answer = re.sub(r'^based on the retrieved document \([^)]+\):\s*', '', answer, flags=re.IGNORECASE).strip().lower()
        q_lower = query_text.lower()
        q_tokens = [w for w in re.findall(r'\w+', q_lower) if w not in ENGLISH_STOPWORDS]

        q_proper_nouns = set(w.lower() for w in re.findall(r'\w+', query_text) if w.lower() not in ENGLISH_STOPWORDS and (re.search(r'\d', w) or w.isupper() or len(w) <= 3 or len(query_text.strip()) <= 4))
        ans_tokens = set(w.lower() for w in re.findall(r'\w+', core_answer) if w.lower() not in ENGLISH_STOPWORDS)
        raw_ans_nums = re.findall(r'\b\d+(?:\.\d+)?%?\b', core_answer)
        standalone_ans_nums = [n for n in raw_ans_nums if not re.search(r'[a-zA-Z]' + re.escape(n), core_answer) and not re.search(re.escape(n) + r'[a-zA-Z]', core_answer)]

        ans_non_entity_tokens = [w for w in ans_tokens if w not in q_proper_nouns]

        q_numeric_keywords = {"mark", "marks", "score", "scores", "total", "count", "number", "percentage", "percent", "ratio", "rate", "cost", "fee", "price", "threshold", "grade", "gpa", "val", "value", "formula"}
        q_requires_numeric = any(t in q_numeric_keywords for t in q_tokens)

        is_bare_entity_answer = bool(q_proper_nouns) and (ans_tokens.issubset(q_proper_nouns) or not ans_non_entity_tokens) and not standalone_ans_nums and len(ans_tokens) <= 3

        for idx, clause in enumerate(clauses):
            sim = float(sims[idx])
            c_tokens = [w.lower() for w in re.findall(r'\w+', clause) if w.lower() not in ENGLISH_STOPWORDS and len(w) > 2]
            token_match = (sum(1 for t in c_tokens if any(t in core_answer or (len(t) >= 3 and len(at) >= 3 and (t.startswith(at[:4]) or at.startswith(t[:4]))) for at in ans_tokens)) / len(c_tokens)) if c_tokens else 1.0

            GENERIC_QUESTION_WORDS = {"what", "how", "why", "when", "where", "who", "which", "is", "are", "was", "were", "formula", "definition", "explanation", "meaning", "details", "overview", "summary"}
            # Aspect Predicate Coverage: Check non-subject tokens in clause
            c_predicate_tokens = [w for w in c_tokens if w not in q_proper_nouns and w not in GENERIC_QUESTION_WORDS]
            c_pred_match = (sum(1 for t in c_predicate_tokens if any(t in core_answer or (len(t) >= 3 and len(at) >= 3 and (t.startswith(at[:4]) or at.startswith(t[:4]))) for at in ans_tokens)) / len(c_predicate_tokens)) if c_predicate_tokens else 1.0

            # If answer is a bare entity code fragment or fails to cover clause predicate tokens, aspect is NOT fully fulfilled
            if is_bare_entity_answer and any(w for w in c_tokens if w not in q_proper_nouns):
                missing_aspects.append(clause[:60])
            elif c_predicate_tokens and c_pred_match < 0.25 and not standalone_ans_nums:
                missing_aspects.append(clause[:60])
            elif (standalone_ans_nums and not is_bare_entity_answer) or (sim >= 0.50 and token_match >= 0.30 and not is_bare_entity_answer):
                covered_count += 1
            else:
                missing_aspects.append(clause[:60])

        coverage_ratio = round(covered_count / total_aspects, 2) if total_aspects > 0 else 1.0

        return {
            "coverage_ratio": coverage_ratio,
            "total_aspects": total_aspects,
            "covered_aspects": covered_count,
            "missing_aspects": missing_aspects
        }



class FailureClassifier:
    """
    Executes the deterministic decision tree to determine the overall evaluation failure category.
    Does NOT use an LLM for decision logic.
    """
    @staticmethod
    def classify_failure(
        evaluation_status: str,
        claims_analysis: list[dict],
        oracle_result: dict,
        has_confirmed_conflict: bool,
        has_suspected_conflict: bool,
        has_topk_evidence: bool,
        coverage_ratio: float = 1.0
    ) -> str:
        # Decision 1: Insufficient / Empty Top-K Evidence
        if not has_topk_evidence or evaluation_status == "NOT_EVALUABLE":
            if oracle_result.get("found"):
                return "RETRIEVAL_FAILURE"
            else:
                return "EVIDENCE_INSUFFICIENCY"

        # Decision 2: Evaluate Top-K Evidence Contradictions, Unsupported Claims, and Irrelevant Evidence
        has_contradictions = any(c.get("support_status") == "CONTRADICTED" for c in claims_analysis)
        has_unsupported = any(c.get("support_status") == "UNSUPPORTED" for c in claims_analysis)
        has_irrelevant = any(c.get("relevance_classification") == "SUPPORTED_IRRELEVANT" for c in claims_analysis)

        if has_contradictions or has_unsupported or has_irrelevant:
            return "UNSUPPORTED_CLAIMS"


        # Decision 3: Incomplete Question Aspect Coverage
        if coverage_ratio < 1.0:
            return "INCOMPLETE_ANSWER"


        # Decision 4: Phase 2 Confirmed Knowledge Conflict
        if has_confirmed_conflict:
            return "KNOWLEDGE_CONFLICT"

        # Default: Well Grounded
        return "WELL_GROUNDED"


class AnswerEvaluator:
    """
    Main Phase 3 Answer Reliability Evaluator Service.
    Computes transparent, bounded Answer Reliability Score S_Ans in [0.0, 100.0],
    handles division-by-zero safely, and outputs structured AnswerEvaluationReport.
    """
    @classmethod
    def evaluate(cls, query: str, answer: str, retrieved_evidence: list[dict], history_file_path: Path = None, owner_id: str = None) -> dict:
        timestamp = datetime.utcnow().isoformat() + "Z"
        eval_id = f"EVAL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


        # -------------------------------------------------------------
        # STEP 1: Check Empty / Insufficient Evidence State
        # -------------------------------------------------------------
        has_topk_evidence = bool(retrieved_evidence and len(retrieved_evidence) > 0)
        
        # Extract Claims
        claims = ClaimExtractor.extract_claims(answer)
        
        if not has_topk_evidence:
            # Execute Full-KB Oracle to check if evidence exists elsewhere in KB
            oracle_res = FullKBRetrievalOracle.search_oracle(query, similarity_threshold=0.50, owner_id=owner_id)
            
            if oracle_res.get("found"):
                # Evidence exists in full KB but was missed in Top-K -> RETRIEVAL_FAILURE
                rep = {
                    "evaluation_id": eval_id,
                    "owner_id": owner_id or "legacy_dev_owner",
                    "timestamp": timestamp,
                    "query": query,
                    "generated_answer": answer,
                    "evaluation_status": "EVALUATED",
                    "overall_reliability_score": 0.0,
                    "reliability_status": "UNRELIABLE",
                    "failure_category": "RETRIEVAL_FAILURE",
                    "hallucination_risk": "HIGH",
                    "scoring_breakdown": {
                        "raw_measurements": {
                            "total_claims": len(claims),
                            "supported_claims": 0,
                            "citation_covered_claims": 0,
                            "top_k_chunks_retrieved": 0,
                            "average_retrieval_similarity": 0.0,
                            "oracle_full_kb_similarity": oracle_res.get("best_similarity", 0.0)
                        },
                        "sub_scores": {
                            "claim_support_score": 0.0,
                            "citation_coverage_score": 0.0,
                            "retrieval_similarity_score": 0.0
                        },
                        "configured_weights": {
                            "support_weight": settings.WEIGHT_CLAIM_SUPPORT,
                            "coverage_weight": settings.WEIGHT_CITATION_COVERAGE,
                            "similarity_weight": settings.WEIGHT_RETRIEVAL_SIMILARITY
                        }
                    },
                    "claim_analysis": claims,
                    "retrieval_analysis": {
                        "total_chunks_retrieved": 0,
                        "average_relevance": 0.0,
                        "retrieval_sufficiency": "RETRIEVAL_FAILED_ORACLE_FOUND"
                    },
                    "phase2_cross_references": []
                }
                EvaluationHistoryService.log_evaluation_run(rep, history_file_path=history_file_path)
                return rep
            else:
                # Zero evidence in Top-K and zero evidence in full KB -> NOT_EVALUABLE / EVIDENCE_INSUFFICIENCY
                rep = {
                    "evaluation_id": eval_id,
                    "timestamp": timestamp,
                    "query": query,
                    "generated_answer": answer,
                    "evaluation_status": "NOT_EVALUABLE",
                    "overall_reliability_score": 0.0,
                    "reliability_status": "NOT_EVALUABLE",
                    "failure_category": "EVIDENCE_INSUFFICIENCY",
                    "hallucination_risk": "UNKNOWN",
                    "scoring_breakdown": {
                        "raw_measurements": {
                            "total_claims": len(claims),
                            "supported_claims": 0,
                            "citation_covered_claims": 0,
                            "top_k_chunks_retrieved": 0,
                            "average_retrieval_similarity": 0.0,
                            "oracle_full_kb_similarity": oracle_res.get("best_similarity", 0.0)
                        },
                        "sub_scores": {
                            "claim_support_score": 0.0,
                            "citation_coverage_score": 0.0,
                            "retrieval_similarity_score": 0.0
                        },
                        "configured_weights": {
                            "support_weight": settings.WEIGHT_CLAIM_SUPPORT,
                            "coverage_weight": settings.WEIGHT_CITATION_COVERAGE,
                            "similarity_weight": settings.WEIGHT_RETRIEVAL_SIMILARITY
                        }
                    },
                    "claim_analysis": claims,
                    "retrieval_analysis": {
                        "total_chunks_retrieved": 0,
                        "average_relevance": 0.0,
                        "retrieval_sufficiency": "INSUFFICIENT_EVIDENCE"
                    },
                    "phase2_cross_references": []
                }
                EvaluationHistoryService.log_evaluation_run(rep, history_file_path=history_file_path)
                return rep



        # -------------------------------------------------------------
        # STEP 2: Claim-Level Evidence Matching & Traceability
        # -------------------------------------------------------------
        claims_analysis, avg_retrieval_sim = EvidenceMatcher.match_claims_to_evidence(claims, retrieved_evidence, query=query)
        coverage_analysis = QuestionAspectAnalyzer.analyze_coverage(query, answer, retrieved_evidence)
        cov_ratio = coverage_analysis["coverage_ratio"]

        # -------------------------------------------------------------
        # STEP 3: Phase 2 Issue Cross-Referencing
        # -------------------------------------------------------------
        phase2_refs, has_confirmed_conf, has_suspected_conf = Phase2CrossReferencer.cross_reference_issues(retrieved_evidence)

        # Execute Full-KB Oracle check for completeness diagnostic
        oracle_res = FullKBRetrievalOracle.search_oracle(query, similarity_threshold=0.50)


        # -------------------------------------------------------------
        # STEP 4: Deterministic Failure Category Classification
        # -------------------------------------------------------------
        failure_category = FailureClassifier.classify_failure(
            evaluation_status="EVALUATED",
            claims_analysis=claims_analysis,
            oracle_result=oracle_res,
            has_confirmed_conflict=has_confirmed_conf,
            has_suspected_conflict=has_suspected_conf,
            has_topk_evidence=has_topk_evidence,
            coverage_ratio=cov_ratio
        )

        # -------------------------------------------------------------
        # STEP 5: Transparent Bounded Score Calculation
        # -------------------------------------------------------------
        tot_claims = len(claims_analysis)
        n_supp = sum(1 for c in claims_analysis if c["support_status"] == "SUPPORTED")
        n_cov = sum(1 for c in claims_analysis if c.get("citation_traceable", False))
        n_rel_supp = sum(1 for c in claims_analysis if c.get("relevance_classification") == "SUPPORTED_RELEVANT")
        n_irrel_supp = sum(1 for c in claims_analysis if c.get("relevance_classification") == "SUPPORTED_IRRELEVANT")

        # Claim Support Sub-score naturally weighted by Question Aspect Coverage
        base_supp = (n_rel_supp / tot_claims) if tot_claims > 0 else 0.0
        s_supp = round((base_supp * cov_ratio) * 100.0, 1)

        s_cov = round((n_cov / tot_claims) * 100.0, 1) if tot_claims > 0 else 0.0
        s_sim = round(avg_retrieval_sim * 100.0, 1)

        w_supp = settings.WEIGHT_CLAIM_SUPPORT
        w_cov = settings.WEIGHT_CITATION_COVERAGE
        w_sim = settings.WEIGHT_RETRIEVAL_SIMILARITY

        composite_score = round((w_supp * s_supp) + (w_cov * s_cov) + (w_sim * s_sim), 1)
        composite_score = max(0.0, min(100.0, composite_score))


        # Status & Hallucination Risk Classification
        n_unsupp = sum(1 for c in claims_analysis if c["support_status"] == "UNSUPPORTED")
        n_contradict = sum(1 for c in claims_analysis if c["support_status"] == "CONTRADICTED")

        # Hallucination Risk strictly measures factual fabrication / contradiction
        if n_contradict > 0 or (tot_claims > 0 and (n_unsupp / tot_claims) > 0.33):
            h_risk = "HIGH"
        elif n_unsupp > 0:
            h_risk = "MEDIUM"
        else:
            h_risk = "LOW"

        # Reliability Status Bounded Thresholds
        # HIGHLY_RELIABLE is POSSIBLE ONLY WHEN failure_category is WELL_GROUNDED,
        # question coverage is complete (cov_ratio == 1.0), and zero unsupported/contradicted/irrelevant claims exist.
        if failure_category == "WELL_GROUNDED" and cov_ratio >= 0.99 and n_unsupp == 0 and n_contradict == 0 and n_irrel_supp == 0:
            if composite_score >= 80.0:
                rel_status = "HIGHLY_RELIABLE"
            elif composite_score >= 60.0:
                rel_status = "PARTIALLY_RELIABLE"
            else:
                rel_status = "UNRELIABLE"
        elif composite_score >= 60.0 and failure_category not in ("RETRIEVAL_FAILURE", "EVIDENCE_INSUFFICIENCY"):
            rel_status = "PARTIALLY_RELIABLE"
        else:
            rel_status = "UNRELIABLE"

        over_gen_risk = "MODERATE" if n_irrel_supp > 0 else "NONE"


        report = {
            "evaluation_id": eval_id,
            "owner_id": owner_id or "legacy_dev_owner",
            "timestamp": timestamp,
            "query": query,
            "generated_answer": answer,
            "evaluation_status": "EVALUATED",
            "overall_reliability_score": composite_score,
            "reliability_status": rel_status,
            "failure_category": failure_category,
            "hallucination_risk": h_risk,
            "over_generation_risk": over_gen_risk,
            "over_generation_detected": n_irrel_supp > 0,
            "question_coverage_analysis": coverage_analysis,


            "over_generation_claims_count": n_irrel_supp,
            "scoring_breakdown": {
                "raw_measurements": {
                    "total_claims": tot_claims,
                    "supported_claims": n_supp,
                    "supported_relevant_claims": n_rel_supp,
                    "supported_irrelevant_claims": n_irrel_supp,
                    "citation_covered_claims": n_cov,
                    "top_k_chunks_retrieved": len(retrieved_evidence),
                    "average_retrieval_similarity": avg_retrieval_sim,
                    "oracle_full_kb_similarity": oracle_res.get("best_similarity", 0.0)
                },
                "sub_scores": {
                    "claim_support_score": s_supp,
                    "citation_coverage_score": s_cov,
                    "retrieval_similarity_score": s_sim
                },
                "configured_weights": {
                    "support_weight": w_supp,
                    "coverage_weight": w_cov,
                    "similarity_weight": w_sim
                }
            },
            "claim_analysis": claims_analysis,
            "retrieval_analysis": {
                "total_chunks_retrieved": len(retrieved_evidence),
                "average_relevance": avg_retrieval_sim,
                "retrieval_sufficiency": "SUFFICIENT"
            },
            "phase2_cross_references": phase2_refs
        }

        EvaluationHistoryService.log_evaluation_run(report, history_file_path=history_file_path)

        return report

answer_evaluator_service = AnswerEvaluator()

