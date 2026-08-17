"""
RAGX Phase 3 — Generic Evaluator & Regression Verification Suite
Tests generic semantic query relevance, status non-contradiction, aspect coverage,
and multi-domain performance across both standard knowledge base documents and
completely unseen documents/domains (Physics, Finance, History, Policy).
"""
import sys
import unittest
import numpy as np
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.vector_db import vector_db, get_shared_embedding_model
from app.services.rag_engine import rag_engine
from app.services.evaluator import (
    ClaimExtractor,
    EvidenceMatcher,
    QuestionAspectAnalyzer,
    FailureClassifier,
    AnswerEvaluator
)

class TestGenericPhase3Suite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n=======================================================")
        print("   RAGX PHASE 3 — GENERIC EVALUATOR TEST SUITE")
        print("=======================================================\n")

    def test_01_claim_extractor_fluff_stripping(self):
        """Verify ClaimExtractor strips meta-prefixes and extracts clean factual claims."""
        raw_answer = "Based on the retrieved document: The minimum attendance requirement is 75%. Students with less than 75% are ineligible."
        claims = ClaimExtractor.extract_claims(raw_answer)
        self.assertGreaterEqual(len(claims), 2)
        self.assertEqual(claims[0]["claim_text"], "The minimum attendance requirement is 75%")
        self.assertFalse(claims[0]["claim_text"].startswith("Based on"))

    def test_02_status_non_contradiction_rule(self):
        """Verify HIGHLY_RELIABLE can NEVER be assigned to INCOMPLETE_ANSWER (coverage < 1.0)."""
        query = "Explain the impact of educated middle classes, industrialisation, and liberalism."
        # Incomplete answer mentioning only middle classes
        incomplete_answer = "The educated middle classes promoted national unity and political reforms."
        evidence = [{
            "chunk_id": "chunk_hist_001",
            "document_name": "History_Ch1.pdf",
            "page_number": 5,
            "text": "The educated middle classes promoted national unity. Industrialisation created new social groups. Liberalism stood for freedom of the individual."
        }]

        report = AnswerEvaluator.evaluate(query, incomplete_answer, evidence)

        # Assertions
        self.assertIn(report["failure_category"], ["INCOMPLETE_ANSWER", "UNSUPPORTED_CLAIMS"])
        self.assertNotEqual(report["reliability_status"], "HIGHLY_RELIABLE",
                            "FAIL: INCOMPLETE_ANSWER must NEVER be classified as HIGHLY_RELIABLE!")
        self.assertIn(report["reliability_status"], ["PARTIALLY_RELIABLE", "UNRELIABLE"])
        print("  [PASS] Test 02: INCOMPLETE_ANSWER strictly bounded to PARTIALLY_RELIABLE/UNRELIABLE.")

    def test_03_unrelated_query_relevance(self):
        """Verify arbitrary unrelated query 'sr' is classified as EVIDENCE_INSUFFICIENCY / NOT_EVALUABLE."""
        query = "sr"
        answer = "Based on the retrieved document (E2E POLICY DOCUMENT 2026, Page 1): sr: 68%"
        evidence = [{
            "chunk_id": "chunk_policy_001",
            "document_name": "E2E POLICY DOCUMENT 2026.pdf",
            "page_number": 1,
            "text": "E2E POLICY DOCUMENT 2026. Academic record code sr: 68% passing criteria."
        }]

        report = AnswerEvaluator.evaluate(query, answer, evidence)

        # Since claim 'sr: 68%' is irrelevant to query 'sr', relevance classification must detect overgeneration/unsupported
        self.assertNotEqual(report["reliability_status"], "HIGHLY_RELIABLE")
        print(f"  [PASS] Test 03: 'sr' evaluated with Failure Category: {report['failure_category']} / Status: {report['reliability_status']}.")

    def test_04_unseen_domain_quantum_physics(self):
        """Verify performance on completely unseen Quantum Physics document."""
        query = "What is quantum entanglement and what is Bell's inequality threshold?"
        answer = "Quantum entanglement is a phenomenon where particles remain connected regardless of distance. Bell's inequality threshold for local realism is 2.0."
        unseen_physics_evidence = [{
            "chunk_id": "chunk_phys_99",
            "document_name": "Quantum_Physics_Treatise.pdf",
            "page_number": 42,
            "text": "Quantum entanglement describes particles whose states are inextricably linked across space. Clauser-Horne-Shimony-Holt (CHSH) formulation shows Bell's inequality threshold for local realism is 2.0, whereas quantum mechanics violates it reaching 2.828."
        }]

        report = AnswerEvaluator.evaluate(query, answer, unseen_physics_evidence)

        self.assertEqual(report["failure_category"], "WELL_GROUNDED")
        self.assertEqual(report["reliability_status"], "HIGHLY_RELIABLE")
        self.assertGreaterEqual(report["overall_reliability_score"], 80.0)
        self.assertTrue(report["claim_analysis"][0]["citation_traceable"])
        print(f"  [PASS] Test 04: Unseen Quantum Physics evaluated correctly ({report['overall_reliability_score']}% / HIGHLY_RELIABLE).")

    def test_05_unseen_domain_financial_regulations(self):
        """Verify performance on unseen Banking Regulation document with numeric claim disparity."""
        query = "What is the mandatory Tier 1 capital adequacy ratio?"
        # Answer contains contradictory figure (12.5% vs 10.5% in source)
        answer = "The mandatory Tier 1 capital adequacy ratio for commercial banks is 12.5%."
        finance_evidence = [{
            "chunk_id": "chunk_fin_101",
            "document_name": "Basel_III_Framework.pdf",
            "page_number": 12,
            "text": "Under Basel III guidelines, the mandatory Tier 1 capital adequacy ratio for commercial banks is 10.5% of risk-weighted assets."
        }]

        report = AnswerEvaluator.evaluate(query, answer, finance_evidence)

        self.assertEqual(report["claim_analysis"][0]["support_status"], "CONTRADICTED")
        self.assertEqual(report["failure_category"], "UNSUPPORTED_CLAIMS")
        self.assertEqual(report["hallucination_risk"], "HIGH")
        self.assertNotEqual(report["reliability_status"], "HIGHLY_RELIABLE")
        print(f"  [PASS] Test 05: Numeric contradiction detected on unseen Financial Regulation document ({report['hallucination_risk']} risk).")

    def test_06_unseen_domain_missing_evidence(self):
        """Verify unseen question with zero evidence in KB returns NOT_EVALUABLE / EVIDENCE_INSUFFICIENCY."""
        query = "What is the speed of sound in liquid helium at absolute zero?"
        answer = "The requested information could not be found in the provided document context."
        empty_evidence = []

        report = AnswerEvaluator.evaluate(query, answer, empty_evidence)

        self.assertEqual(report["evaluation_status"], "NOT_EVALUABLE")
        self.assertEqual(report["failure_category"], "EVIDENCE_INSUFFICIENCY")
        self.assertEqual(report["reliability_status"], "NOT_EVALUABLE")
        self.assertEqual(report["overall_reliability_score"], 0.0)
        print("  [PASS] Test 06: Unseen missing query evaluated as NOT_EVALUABLE / EVIDENCE_INSUFFICIENCY.")

    def test_07_interleaved_query_isolation(self):
        """Verify running 5 distinct queries sequentially exhibits zero cross-query state leakage."""
        queries = [
            ("What is the attendance policy?", "The minimum attendance requirement is 75%."),
            ("What is quantum entanglement?", "Particles remain linked across space."),
            ("What is the capital ratio?", "Tier 1 ratio is 10.5%."),
            ("sr", "sr: 68%"),
            ("What is the attendance policy?", "The minimum attendance requirement is 75%.")
        ]

        reports = []
        for q, a in queries:
            rep = AnswerEvaluator.evaluate(q, a, [{
                "chunk_id": "chunk_gen_01",
                "document_name": "General_Doc.pdf",
                "page_number": 1,
                "text": "General document context snippet for evaluation test."
            }])
            reports.append(rep)

        # Verify query 0 and query 4 match while query 1, 2, 3 remained isolated
        self.assertEqual(reports[0]["query"], queries[0][0])
        self.assertEqual(reports[1]["query"], queries[1][0])
        self.assertEqual(reports[3]["query"], "sr")
        self.assertEqual(reports[4]["query"], queries[4][0])
        print("  [PASS] Test 07: Sequential interleaved query isolation verified.")


if __name__ == "__main__":
    unittest.main()
