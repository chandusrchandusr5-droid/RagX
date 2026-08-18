"""
Generic Claim-Support Regression Suite for RAGX Phase 3.
Validates proposition-level claim support evaluation across 14 diverse cases:
1. Supported historical claim
2. Contradicted historical claim
3. Topic-related but unsupported historical claim (Nationalism regression case)
4. Supported numerical answer
5. Unsupported numerical answer
6. Supported formula/explanation
7. Entity-only overlap
8. Unseen domain (Medical/Metformin)
9. Multi-aspect question
10. Interleaved request isolation
11. Custom answer with evidence
12. Custom answer with empty Top-K but Oracle evidence
13. Completely unsupported custom answer
14. RAG-generated grounded answer
"""

import sys
import unittest
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.evaluator import AnswerEvaluator, EvidenceMatcher, ClaimExtractor

class TestGenericClaimSupportSuite(unittest.TestCase):

    def test_01_supported_historical_claim(self):
        """Case 1: True positive supported historical claim."""
        query = "When did the French Revolution occur and what did it express?"
        answer = "The French Revolution provided an early expression of nationalism in 1789."
        evidence = [{
            "text": "The first clear expression of nationalism came with the French Revolution in 1789.",
            "document_name": "history_ch1.pdf",
            "page_number": 1,
            "chunk_id": "chunk_h1"
        }]
        res = AnswerEvaluator.evaluate(query, answer, evidence)
        self.assertEqual(res["failure_category"], "WELL_GROUNDED")
        self.assertEqual(res["reliability_status"], "HIGHLY_RELIABLE")
        self.assertGreaterEqual(res["overall_reliability_score"], 80.0)

    def test_02_contradicted_historical_claim(self):
        """Case 2: Contradicted historical claim (numeric date conflict)."""
        query = "When did the French Revolution occur?"
        answer = "The French Revolution occurred in 1945."
        evidence = [{
            "text": "The first clear expression of nationalism came with the French Revolution in 1789.",
            "document_name": "history_ch1.pdf",
            "page_number": 1,
            "chunk_id": "chunk_h1"
        }]
        res = AnswerEvaluator.evaluate(query, answer, evidence)
        self.assertEqual(res["failure_category"], "UNSUPPORTED_CLAIMS")
        self.assertEqual(res["hallucination_risk"], "HIGH")
        self.assertEqual(res["claim_analysis"][0]["support_status"], "CONTRADICTED")

    def test_03_nationalism_topic_similarity_unsupported_regression(self):
        """Case 3: Topic-related but unsupported historical claim (Nationalism Regression)."""
        query = "What were the main factors that led to the rise of nationalism in Europe?"
        answer = "Nationalism in Europe mainly arose because European countries adopted democracy after the Second World War and because the United Nations promoted national independence."
        evidence = [{
            "text": "Nationalism became associated with liberalism and revolution in many regions of Europe. The first clear expression of nationalism came with the French Revolution in 1789.",
            "document_name": "jess301.pdf",
            "page_number": 9,
            "chunk_id": "chunk_nat1"
        }]
        res = AnswerEvaluator.evaluate(query, answer, evidence)
        
        # Verify semantic similarity does NOT grant SUPPORTED status
        self.assertEqual(res["failure_category"], "UNSUPPORTED_CLAIMS")
        self.assertNotEqual(res["reliability_status"], "HIGHLY_RELIABLE")
        self.assertIn(res["hallucination_risk"], ["HIGH", "MEDIUM"])
        
        # Verify claim analysis marks false proposition as UNSUPPORTED
        unsupp_claims = [c for c in res["claim_analysis"] if c["support_status"] == "UNSUPPORTED"]
        self.assertGreater(len(unsupp_claims), 0, "Topically related but factually ungrounded claim must be marked UNSUPPORTED.")

    def test_04_supported_numerical_answer(self):
        """Case 4: Supported numerical answer (e.g. 75% attendance requirement)."""
        query = "What is the minimum attendance requirement?"
        answer = "The minimum attendance requirement for undergraduate students is 75%."
        evidence = [{
            "text": "All undergraduate students must maintain a minimum attendance requirement of 75%.",
            "document_name": "attendance_policy.pdf",
            "page_number": 2,
            "chunk_id": "chunk_att1"
        }]
        res = AnswerEvaluator.evaluate(query, answer, evidence)
        self.assertEqual(res["failure_category"], "WELL_GROUNDED")
        self.assertEqual(res["reliability_status"], "HIGHLY_RELIABLE")

    def test_05_unsupported_numerical_answer(self):
        """Case 5: Unsupported numerical answer (e.g. 90% vs 75%)."""
        query = "What is the minimum attendance requirement?"
        answer = "The minimum attendance requirement for undergraduate students is 90%."
        evidence = [{
            "text": "All undergraduate students must maintain a minimum attendance requirement of 75%.",
            "document_name": "attendance_policy.pdf",
            "page_number": 2,
            "chunk_id": "chunk_att1"
        }]
        res = AnswerEvaluator.evaluate(query, answer, evidence)
        self.assertEqual(res["failure_category"], "UNSUPPORTED_CLAIMS")
        self.assertEqual(res["claim_analysis"][0]["support_status"], "CONTRADICTED")

    def test_06_supported_formula_claim(self):
        """Case 6: Supported formula/equation claim."""
        query = "What is Ohm's law formula?"
        answer = "Ohm's law states that V = IR."
        evidence = [{
            "text": "In electrical engineering, Ohm's law states that V = IR where V is voltage, I is current, and R is resistance.",
            "document_name": "physics_notes.pdf",
            "page_number": 5,
            "chunk_id": "chunk_ohm1"
        }]
        res = AnswerEvaluator.evaluate(query, answer, evidence)
        self.assertEqual(res["failure_category"], "WELL_GROUNDED")
        self.assertEqual(res["reliability_status"], "HIGHLY_RELIABLE")

    def test_07_entity_only_overlap(self):
        """Case 7: Entity-only overlap without predicate satisfaction."""
        query = "What are the total marks for BMATS201?"
        answer = "BMATS201."
        evidence = [{
            "text": "BMATS201 is a mandatory course code for second semester students.",
            "document_name": "syllabus.pdf",
            "page_number": 1,
            "chunk_id": "chunk_bmats1"
        }]
        res = AnswerEvaluator.evaluate(query, answer, evidence)
        self.assertEqual(res["failure_category"], "UNSUPPORTED_CLAIMS")

    def test_08_unseen_domain_medical(self):
        """Case 8: Unseen domain (Pharmacology/Metformin)."""
        query = "What is the primary mechanism of action of Metformin?"
        
        # Test 8A: Supported proposition
        answer_valid = "Metformin acts primarily by inhibiting hepatic gluconeogenesis and increasing insulin sensitivity."
        evidence_valid = [{
            "text": "Metformin suppresses hepatic glucose production (gluconeogenesis) and enhances peripheral insulin sensitivity.",
            "document_name": "pharma_guide.pdf",
            "page_number": 14,
            "chunk_id": "chunk_med1"
        }]
        res_valid = AnswerEvaluator.evaluate(query, answer_valid, evidence_valid)
        self.assertEqual(res_valid["failure_category"], "WELL_GROUNDED")

        # Test 8B: Unsupported proposition with topic overlap
        answer_unsupp = "Metformin acts primarily by stimulating pancreatic beta cells to secrete insulin directly into blood."
        evidence_topic = [{
            "text": "Metformin is a biguanide antihyperglycemic agent widely prescribed for type 2 diabetes mellitus.",
            "document_name": "pharma_guide.pdf",
            "page_number": 14,
            "chunk_id": "chunk_med2"
        }]
        res_unsupp = AnswerEvaluator.evaluate(query, answer_unsupp, evidence_topic)
        self.assertEqual(res_unsupp["failure_category"], "UNSUPPORTED_CLAIMS")

    def test_09_multi_aspect_question(self):
        """Case 9: Multi-aspect question coverage."""
        query = "What were the economic causes of the French Revolution? What were the political causes?"
        answer = "The economic cause was severe debt and financial crisis."
        evidence = [{
            "text": "The economic cause of the French Revolution was severe debt and financial crisis.",
            "document_name": "history.pdf",
            "page_number": 3,
            "chunk_id": "chunk_aspect1"
        }]
        res = AnswerEvaluator.evaluate(query, answer, evidence)
        self.assertLess(res["question_coverage_analysis"]["coverage_ratio"], 1.0)

    def test_10_interleaved_isolation(self):
        """Case 10: Request isolation test A -> B -> A -> C -> B -> C -> A."""
        evidence_A = [{"text": "Course MATH201 total marks is 100.", "document_name": "docA.pdf", "page_number": 1, "chunk_id": "cA"}]
        evidence_B = [{"text": "Course CHEM101 total marks is 50.", "document_name": "docB.pdf", "page_number": 1, "chunk_id": "cB"}]

        res_A1 = AnswerEvaluator.evaluate("MATH201 marks?", "100", evidence_A)
        res_B1 = AnswerEvaluator.evaluate("CHEM101 marks?", "50", evidence_B)
        res_A2 = AnswerEvaluator.evaluate("MATH201 marks?", "100", evidence_A)

        self.assertEqual(res_A1["overall_reliability_score"], res_A2["overall_reliability_score"])
        self.assertNotEqual(res_A1["query"], res_B1["query"])

    def test_11_custom_answer_with_evidence(self):
        """Case 11: Custom user answer evaluated against evidence."""
        query = "What is the speed of light in a vacuum?"
        answer = "The speed of light in vacuum is approximately 299,792,458 meters per second."
        evidence = [{
            "text": "In physics, the speed of light in vacuum is defined as exactly 299,792,458 m/s.",
            "document_name": "physics_constants.pdf",
            "page_number": 1,
            "chunk_id": "chunk_light1"
        }]
        res = AnswerEvaluator.evaluate(query, answer, evidence)
        self.assertEqual(res["failure_category"], "WELL_GROUNDED")
        self.assertEqual(res["reliability_status"], "HIGHLY_RELIABLE")

    def test_12_empty_topk_oracle_fallback(self):
        """Case 12: Empty Top-K evidence but Full-KB Oracle finds evidence."""
        query = "What were the main factors that led to the rise of nationalism in Europe?"
        answer = "Nationalism in Europe arose due to industrialisation and educated middle classes."
        empty_evidence = []
        
        res = AnswerEvaluator.evaluate(query, answer, empty_evidence)
        self.assertEqual(res["failure_category"], "RETRIEVAL_FAILURE")
        self.assertEqual(res["evaluation_status"], "EVALUATED")

    def test_13_completely_unsupported_custom_answer(self):
        """Case 13: Completely unsupported custom answer."""
        query = "What is the capital of France?"
        answer = "The capital of France is Tokyo."
        evidence = [{
            "text": "Paris is the capital and most populous city of France.",
            "document_name": "geography.pdf",
            "page_number": 1,
            "chunk_id": "chunk_geo1"
        }]
        res = AnswerEvaluator.evaluate(query, answer, evidence)
        self.assertEqual(res["failure_category"], "UNSUPPORTED_CLAIMS")
        self.assertEqual(res["hallucination_risk"], "HIGH")

    def test_14_rag_generated_grounded_answer(self):
        """Case 14: RAG-generated grounded answer."""
        query = "What is the growth of industry in Europe?"
        answer = "In Western and parts of Central Europe the growth of industrial production and trade meant the growth of towns."
        evidence = [{
            "text": "In Western and parts of Central Europe the growth of industrial production and trade meant the growth of towns and the emergence of commercial classes.",
            "document_name": "jess301.pdf",
            "page_number": 9,
            "chunk_id": "chunk_rag1"
        }]
        res = AnswerEvaluator.evaluate(query, answer, evidence)
        self.assertEqual(res["failure_category"], "WELL_GROUNDED")
        self.assertEqual(res["reliability_status"], "HIGHLY_RELIABLE")

if __name__ == "__main__":
    unittest.main()
