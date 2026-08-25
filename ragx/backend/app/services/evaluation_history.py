import json
import logging
from pathlib import Path
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger("ragx.evaluation_history")

class EvaluationHistoryService:
    @classmethod
    def _load_history(cls, history_file_path: Path = None) -> list[dict]:
        history_file = history_file_path or settings.EVAL_HISTORY_FILE
        if not history_file.exists():
            return []
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                content = f.read()
                if not content.strip():
                    return []
                try:
                    data = json.loads(content)
                except Exception:
                    # Fallback for concatenated or corrupted JSON files
                    decoder = json.JSONDecoder()
                    data, _ = decoder.raw_decode(content)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to read evaluation history file '{history_file}': {e}")
            return []

    @classmethod
    def _save_history(cls, records: list[dict], history_file_path: Path = None):
        history_file = history_file_path or settings.EVAL_HISTORY_FILE
        try:
            temp_file = history_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
            temp_file.replace(history_file)
        except Exception as e:
            logger.error(f"Failed to save evaluation history file '{history_file}': {e}")

    @classmethod
    def log_evaluation_run(cls, report: dict, history_file_path: Path = None, owner_id: str = None) -> dict:
        """
        Logs a Phase 3 Answer Evaluation run to persistent evaluation_history.json.
        Retains compact analytics summary fields plus structured claim analysis & 5-tuple citations.
        """
        records = cls._load_history(history_file_path=history_file_path)

        
        scoring_breakdown = report.get("scoring_breakdown", {})
        raw_m = scoring_breakdown.get("raw_measurements", {})
        retrieval_analysis = report.get("retrieval_analysis", {})

        history_entry = {
            "evaluation_id": report.get("evaluation_id"),
            "owner_id": owner_id or report.get("owner_id", "legacy_dev_owner"),
            "timestamp": report.get("timestamp"),
            "query": report.get("query"),
            "generated_answer": report.get("generated_answer"),
            "evaluation_status": report.get("evaluation_status", "EVALUATED"),
            "overall_reliability_score": report.get("overall_reliability_score", 0.0),
            "reliability_status": report.get("reliability_status", "NOT_EVALUABLE"),
            "failure_category": report.get("failure_category", "EVIDENCE_INSUFFICIENCY"),
            "hallucination_risk": report.get("hallucination_risk", "UNKNOWN"),
            "retrieved_evidence_count": raw_m.get("top_k_chunks_retrieved", 0),
            "total_claims": raw_m.get("total_claims", 0),
            "supported_claims": raw_m.get("supported_claims", 0),
            "citation_covered_claims": raw_m.get("citation_covered_claims", 0),
            "average_retrieval_similarity": raw_m.get("average_retrieval_similarity", 0.0),
            "oracle_full_kb_similarity": raw_m.get("oracle_full_kb_similarity", 0.0),
            "claim_analysis": report.get("claim_analysis", []),
            "phase2_cross_references": report.get("phase2_cross_references", [])
        }

        # Keep latest 500 evaluation records to prevent uncontrolled disk growth
        records.append(history_entry)
        if len(records) > 500:
            records = records[-500:]

        cls._save_history(records, history_file_path=history_file_path)
        logger.info(f"Logged evaluation run '{history_entry['evaluation_id']}' for owner '{history_entry['owner_id']}'.")
        return history_entry


    @classmethod
    def get_history(cls, limit: int = 50, owner_id: str = None) -> list[dict]:
        records = cls._load_history()
        if owner_id:
            allowed = {owner_id, "legacy_dev_owner", "default_workspace", None}
            records = [r for r in records if r.get("owner_id", "legacy_dev_owner") in allowed]
        # Sort by timestamp descending
        sorted_records = sorted(records, key=lambda x: x.get("timestamp", ""), reverse=True)
        return sorted_records[:limit]

    @classmethod
    def get_analytics_summary(cls, owner_id: str = None) -> dict:
        records = cls._load_history()
        if owner_id:
            allowed = {owner_id, "legacy_dev_owner", "default_workspace", None}
            records = [r for r in records if r.get("owner_id", "legacy_dev_owner") in allowed]

        total_runs = len(records)

        if total_runs == 0:
            return {
                "total_evaluations": 0,
                "average_reliability_score": 0.0,
                "reliability_status_distribution": {
                    "HIGHLY_RELIABLE": 0,
                    "PARTIALLY_RELIABLE": 0,
                    "UNRELIABLE": 0,
                    "NOT_EVALUABLE": 0
                },
                "failure_category_distribution": {
                    "WELL_GROUNDED": 0,
                    "GENERATION_FAILURE": 0,
                    "RETRIEVAL_FAILURE": 0,
                    "KNOWLEDGE_CONFLICT": 0,
                    "EVIDENCE_INSUFFICIENCY": 0
                },
                "average_retrieval_similarity": 0.0,
                "score_distribution_buckets": {
                    "85_to_100": 0,
                    "65_to_84": 0,
                    "0_to_64": 0
                },
                "recent_evaluations": []
            }

        scores = [r.get("overall_reliability_score", 0.0) for r in records if r.get("evaluation_status") == "EVALUATED"]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        rel_dist = {
            "HIGHLY_RELIABLE": 0,
            "PARTIALLY_RELIABLE": 0,
            "UNRELIABLE": 0,
            "NOT_EVALUABLE": 0
        }
        
        fail_dist = {
            "WELL_GROUNDED": 0,
            "GENERATION_FAILURE": 0,
            "RETRIEVAL_FAILURE": 0,
            "KNOWLEDGE_CONFLICT": 0,
            "EVIDENCE_INSUFFICIENCY": 0
        }

        buckets = {
            "85_to_100": 0,
            "65_to_84": 0,
            "0_to_64": 0
        }

        sims = []

        for r in records:
            status = r.get("reliability_status", "NOT_EVALUABLE")
            cat = r.get("failure_category", "EVIDENCE_INSUFFICIENCY")
            score = r.get("overall_reliability_score", 0.0)
            sim = r.get("average_retrieval_similarity", 0.0)

            if status in rel_dist:
                rel_dist[status] += 1
            else:
                rel_dist["NOT_EVALUABLE"] += 1

            if cat in fail_dist:
                fail_dist[cat] += 1
            else:
                fail_dist["EVIDENCE_INSUFFICIENCY"] += 1

            if r.get("evaluation_status") == "EVALUATED":
                if score >= 85.0:
                    buckets["85_to_100"] += 1
                elif score >= 65.0:
                    buckets["65_to_84"] += 1
                else:
                    buckets["0_to_64"] += 1

            sims.append(sim)

        avg_sim = round(sum(sims) / len(sims), 4) if sims else 0.0

        sorted_recent = sorted(records, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]

        return {
            "total_evaluations": total_runs,
            "average_reliability_score": avg_score,
            "reliability_status_distribution": rel_dist,
            "failure_category_distribution": fail_dist,
            "average_retrieval_similarity": avg_sim,
            "score_distribution_buckets": buckets,
            "recent_evaluations": sorted_recent
        }
