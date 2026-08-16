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
            if len(sentence_clean) > 8:
                claims.append({
                    "claim_id": f"CLM-{claim_counter:03d}",
                    "claim_text": sentence_clean
                })
                claim_counter += 1

        # Fallback if sentence splitting produced nothing
        if not claims and len(cleaned) > 5:
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
    def search_oracle(query: str, similarity_threshold: float = 0.50) -> dict:

        try:
            all_chunks = vector_db.get_all_chunks()
            if not all_chunks or not all_chunks.get("documents"):
                return {"found": False, "best_similarity": 0.0, "best_chunk": None}

            documents = all_chunks["documents"]
            metadatas = all_chunks["metadatas"]
            embeddings = all_chunks.get("embeddings")

            if embeddings is None or len(embeddings) == 0:
                return {"found": False, "best_similarity": 0.0, "best_chunk": None}

            model = get_embedding_model()
            q_emb = model.encode(query, convert_to_numpy=True)
            q_norm = q_emb / (np.linalg.norm(q_emb) + 1e-9)

            best_sim = 0.0
            best_idx = 0

            for idx, (doc, emb) in enumerate(zip(documents, embeddings)):
                emb_arr = np.array(emb)
                v_norm = emb_arr / (np.linalg.norm(emb_arr) + 1e-9)
                v_sim = float(np.dot(v_norm, q_norm))
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
    Strictly verifies 5-tuple citation traceability:
    claim -> evidence_chunk -> chunk_id -> document_name -> page_number.
    """
    @staticmethod
    def match_claims_to_evidence(claims: list[dict], retrieved_chunks: list[dict]) -> tuple[list[dict], float]:
        if not claims or not retrieved_chunks:
            return claims, 0.0

        model = get_embedding_model()
        num_pattern = re.compile(r'\d{1,3}%|\d{1,3}\s*marks|\d{1,3}\s*percent')

        # Encode claim embeddings and chunk embeddings
        claim_texts = [c["claim_text"] for c in claims]
        chunk_texts = [c.get("text", "") for c in retrieved_chunks]

        claim_embs = model.encode(claim_texts, convert_to_numpy=True)
        chunk_embs = model.encode(chunk_texts, convert_to_numpy=True)

        # Normalize
        claim_norms = claim_embs / (np.linalg.norm(claim_embs, axis=1, keepdims=True) + 1e-9)
        chunk_norms = chunk_embs / (np.linalg.norm(chunk_embs, axis=1, keepdims=True) + 1e-9)

        # Cosine similarity matrix: N_claims x N_chunks
        sim_matrix = np.dot(claim_norms, chunk_norms.T)

        matched_claims = []
        all_top_sims = []

        for i, claim in enumerate(claims):
            c_text = claim["claim_text"]
            best_chunk_idx = int(np.argmax(sim_matrix[i]))
            best_sim = float(sim_matrix[i, best_chunk_idx])
            all_top_sims.append(best_sim)

            best_chunk = retrieved_chunks[best_chunk_idx]
            ev_text = best_chunk.get("text", "")
            chunk_id = best_chunk.get("id") or best_chunk.get("chunk_id", "N/A")
            doc_name = best_chunk.get("document_name", "Unknown")
            page_num = best_chunk.get("page_number", 1)

            # Extract numeric figures for numeric disparity check
            claim_nums = num_pattern.findall(c_text.lower())
            ev_nums = num_pattern.findall(ev_text.lower())

            # Determine Support Status
            if claim_nums and ev_nums and set(claim_nums) != set(ev_nums) and best_sim >= 0.60:
                support_status = "CONTRADICTED"
                disparity_detail = f"Claim mentions '{', '.join(claim_nums)}' while evidence states '{', '.join(ev_nums)}'."
            elif best_sim >= 0.70:
                support_status = "SUPPORTED"
                disparity_detail = "Claim is semantically supported by retrieved evidence snippet."
            elif best_sim >= 0.50:
                support_status = "UNSUPPORTED"
                disparity_detail = "Partial semantic overlap, but specific claim facts are absent from evidence."
            else:
                support_status = "UNSUPPORTED"
                disparity_detail = "Low semantic similarity to retrieved evidence context."

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
        has_topk_evidence: bool
    ) -> str:
        # Decision 1: Insufficient / Empty Top-K Evidence
        if not has_topk_evidence or evaluation_status == "NOT_EVALUABLE":
            if oracle_result.get("found"):
                return "RETRIEVAL_FAILURE"
            else:
                return "EVIDENCE_INSUFFICIENCY"

        # Decision 2: Evaluate Top-K Evidence Contradictions & Unsupported Claims
        has_contradictions = any(c["support_status"] == "CONTRADICTED" for c in claims_analysis)
        has_unsupported = any(c["support_status"] == "UNSUPPORTED" for c in claims_analysis)

        if has_contradictions or has_unsupported:
            return "GENERATION_FAILURE"

        # Decision 3: Phase 2 Confirmed Knowledge Conflict
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
    def evaluate(cls, query: str, answer: str, retrieved_evidence: list[dict], history_file_path: Path = None) -> dict:
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
            oracle_res = FullKBRetrievalOracle.search_oracle(query, similarity_threshold=0.50)
            
            if oracle_res.get("found"):
                # Evidence exists in full KB but was missed in Top-K -> RETRIEVAL_FAILURE
                rep = {
                    "evaluation_id": eval_id,
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
        claims_analysis, avg_retrieval_sim = EvidenceMatcher.match_claims_to_evidence(claims, retrieved_evidence)

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
            has_topk_evidence=has_topk_evidence
        )

        # -------------------------------------------------------------
        # STEP 5: Transparent Bounded Score Calculation
        # -------------------------------------------------------------
        tot_claims = len(claims_analysis)
        n_supp = sum(1 for c in claims_analysis if c["support_status"] == "SUPPORTED")
        n_cov = sum(1 for c in claims_analysis if c.get("citation_traceable", False))

        # Division-by-zero safe sub-scores
        s_supp = round((n_supp / tot_claims) * 100.0, 1) if tot_claims > 0 else 0.0
        s_cov = round((n_cov / tot_claims) * 100.0, 1) if tot_claims > 0 else 0.0
        s_sim = round(avg_retrieval_sim * 100.0, 1)

        w_supp = settings.WEIGHT_CLAIM_SUPPORT
        w_cov = settings.WEIGHT_CITATION_COVERAGE
        w_sim = settings.WEIGHT_RETRIEVAL_SIMILARITY

        composite_score = round((w_supp * s_supp) + (w_cov * s_cov) + (w_sim * s_sim), 1)
        composite_score = max(0.0, min(100.0, composite_score))

        # Status Classification
        if composite_score >= 85.0:
            rel_status = "HIGHLY_RELIABLE"
            h_risk = "LOW"
        elif composite_score >= 65.0:
            rel_status = "PARTIALLY_RELIABLE"
            h_risk = "MEDIUM"
        else:
            rel_status = "UNRELIABLE"
            h_risk = "HIGH"

        report = {
            "evaluation_id": eval_id,
            "timestamp": timestamp,
            "query": query,
            "generated_answer": answer,
            "evaluation_status": "EVALUATED",
            "overall_reliability_score": composite_score,
            "reliability_status": rel_status,
            "failure_category": failure_category,
            "hallucination_risk": h_risk,
            "scoring_breakdown": {
                "raw_measurements": {
                    "total_claims": tot_claims,
                    "supported_claims": n_supp,
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

