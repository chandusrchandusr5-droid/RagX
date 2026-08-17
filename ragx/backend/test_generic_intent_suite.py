import unittest
import sys
import json
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.evaluator import AnswerEvaluator, EvidenceMatcher, QuestionAspectAnalyzer

class TestGenericIntentSuite(unittest.TestCase):
    """
    Validation test suite ensuring RAGX distinguishes Entity-Presence from Question-Fulfillment
    across arbitrary domains and query types without hardcoded topic rules.
    """

    def test_01_entity_only_answer(self):
        """Case A: Q: 'What is the formula for calculating total marks in BMATS201?' A: 'BMATS201' -> INCOMPLETE_ANSWER / NOT HIGHLY_RELIABLE"""
        query = "What is the formula for calculating total marks in BMATS201?"
        answer = "Based on the retrieved document (2ND SEM RESULT.pdf, Page 1): BMATS201"
        evidence = [{
            "chunk_id": "chunk_001",
            "document_name": "2ND SEM RESULT.pdf",
            "page_number": 1,
            "text": "BMATS201 MATHEMATICS-II FOR CSE STREAM 15 20 35 P"
        }]

        report = AnswerEvaluator.evaluate(query, answer, evidence)
        print(f"\n[Test 1 Entity-Only] Score: {report['overall_reliability_score']}%, Status: {report['reliability_status']}, Category: {report['failure_category']}")

        self.assertNotEqual(report["reliability_status"], "HIGHLY_RELIABLE", "Entity-only answer MUST NEVER be HIGHLY_RELIABLE!")
        self.assertIn(report["failure_category"], ["INCOMPLETE_ANSWER", "UNSUPPORTED_CLAIMS"], "Should be classified as INCOMPLETE_ANSWER or equivalent.")
        self.assertLessEqual(report["overall_reliability_score"], 60.0, "Score must reflect incomplete predicate fulfillment.")

    def test_02_short_valid_factual_answer(self):
        """Case B: Q: 'What is the minimum passing mark for BMATS201?' A: '35 marks' -> WELL_GROUNDED / HIGHLY_RELIABLE"""
        query = "What is the minimum passing mark for BMATS201?"
        answer = "Based on the retrieved document (2ND SEM RESULT.pdf, Page 1): 35 marks"
        evidence = [{
            "chunk_id": "chunk_001",
            "document_name": "2ND SEM RESULT.pdf",
            "page_number": 1,
            "text": "BMATS201 MATHEMATICS-II FOR CSE STREAM 15 20 35 marks obtained."
        }]

        report = AnswerEvaluator.evaluate(query, answer, evidence)
        print(f"[Test 2 Short Valid] Score: {report['overall_reliability_score']}%, Status: {report['reliability_status']}, Category: {report['failure_category']}")

        self.assertEqual(report["failure_category"], "WELL_GROUNDED")
        self.assertEqual(report["reliability_status"], "HIGHLY_RELIABLE")
        self.assertGreaterEqual(report["overall_reliability_score"], 80.0)

    def test_03_full_explanatory_answer(self):
        """Case C: Q: 'What is the formula for calculating total marks in BMATS201?' A: Explanatory formula -> WELL_GROUNDED / HIGHLY_RELIABLE"""
        query = "What is the formula for calculating total marks in BMATS201?"
        answer = "Based on the retrieved document (2ND SEM RESULT.pdf, Page 1): Total marks are calculated by adding Internal Marks and External Marks."
        evidence = [{
            "chunk_id": "chunk_001",
            "document_name": "2ND SEM RESULT.pdf",
            "page_number": 1,
            "text": "BMATS201 Internal Marks and External Marks are added together to calculate total marks."
        }]

        report = AnswerEvaluator.evaluate(query, answer, evidence)
        print(f"[Test 3 Full Explanatory] Score: {report['overall_reliability_score']}%, Status: {report['reliability_status']}, Category: {report['failure_category']}")

        self.assertEqual(report["failure_category"], "WELL_GROUNDED")
        self.assertEqual(report["reliability_status"], "HIGHLY_RELIABLE")
        self.assertGreaterEqual(report["overall_reliability_score"], 80.0)

    def test_04_different_domain_entity_only(self):
        """Test 4: Unseen Domain (Quantum Physics): Q: 'What is the threshold for Bell inequality violation in CHSH?' A: 'CHSH' -> INCOMPLETE_ANSWER"""
        query = "What is the threshold value for Bell inequality violation in CHSH?"
        answer = "Based on the retrieved document (Quantum_Physics.pdf, Page 4): CHSH"
        evidence = [{
            "chunk_id": "chunk_phys_001",
            "document_name": "Quantum_Physics.pdf",
            "page_number": 4,
            "text": "The CHSH inequality states that local realism is violated if S > 2.0."
        }]

        report = AnswerEvaluator.evaluate(query, answer, evidence)
        print(f"[Test 4 Unseen Domain Entity-Only] Score: {report['overall_reliability_score']}%, Status: {report['reliability_status']}, Category: {report['failure_category']}")

        self.assertNotEqual(report["reliability_status"], "HIGHLY_RELIABLE")
        self.assertIn(report["failure_category"], ["INCOMPLETE_ANSWER", "UNSUPPORTED_CLAIMS"])

    def test_05_unseen_short_numeric_valid_answer(self):
        """Test 5: Unseen Domain (Attendance Policy): Q: 'What is the minimum attendance requirement?' A: '75%' -> WELL_GROUNDED / HIGHLY_RELIABLE"""
        query = "What is the minimum attendance requirement?"
        answer = "Based on the retrieved document (Unseen_Policy_Doc.pdf, Page 1): 75%"
        evidence = [{
            "chunk_id": "chunk_att_001",
            "document_name": "Unseen_Policy_Doc.pdf",
            "page_number": 1,
            "text": "All students must maintain a minimum attendance requirement of 75% in all modules."
        }]

        report = AnswerEvaluator.evaluate(query, answer, evidence)
        print(f"[Test 5 Unseen Short Valid] Score: {report['overall_reliability_score']}%, Status: {report['reliability_status']}, Category: {report['failure_category']}")

        self.assertEqual(report["failure_category"], "WELL_GROUNDED")
        self.assertEqual(report["reliability_status"], "HIGHLY_RELIABLE")

    def test_06_interleaved_query_isolation(self):
        """Test 6: Sequence A -> B -> A -> C -> B -> C -> A verifying zero state leakage & deterministic outputs"""
        sequence = [
            ("A", "What is the minimum attendance requirement?", "Based on Attendance_Policy.pdf: 75%", [{
                "chunk_id": "c1", "document_name": "Attendance_Policy.pdf", "page_number": 1,
                "text": "All students must maintain a minimum attendance requirement of 75%."
            }]),
            ("B", "What is the formula for calculating total marks in BMATS201?", "BMATS201", [{
                "chunk_id": "c2", "document_name": "2ND SEM RESULT.pdf", "page_number": 1,
                "text": "BMATS201 MATHEMATICS-II FOR CSE STREAM 15 20 35 P"
            }]),
            ("A", "What is the minimum attendance requirement?", "Based on Attendance_Policy.pdf: 75%", [{
                "chunk_id": "c1", "document_name": "Attendance_Policy.pdf", "page_number": 1,
                "text": "All students must maintain a minimum attendance requirement of 75%."
            }]),
            ("C", "What is the threshold value for Bell inequality violation in CHSH?", "S > 2.0", [{
                "chunk_id": "c3", "document_name": "Quantum_Physics.pdf", "page_number": 4,
                "text": "The CHSH inequality states that local realism is violated if S > 2.0."
            }]),
            ("B", "What is the formula for calculating total marks in BMATS201?", "BMATS201", [{
                "chunk_id": "c2", "document_name": "2ND SEM RESULT.pdf", "page_number": 1,
                "text": "BMATS201 MATHEMATICS-II FOR CSE STREAM 15 20 35 P"
            }]),
            ("C", "What is the threshold value for Bell inequality violation in CHSH?", "S > 2.0", [{
                "chunk_id": "c3", "document_name": "Quantum_Physics.pdf", "page_number": 4,
                "text": "The CHSH inequality states that local realism is violated if S > 2.0."
            }]),
            ("A", "What is the minimum attendance requirement?", "Based on Attendance_Policy.pdf: 75%", [{
                "chunk_id": "c1", "document_name": "Attendance_Policy.pdf", "page_number": 1,
                "text": "All students must maintain a minimum attendance requirement of 75%."
            }])
        ]

        results_by_type = {"A": [], "B": [], "C": []}
        for code, q, a, ev in sequence:
            rep = AnswerEvaluator.evaluate(q, a, ev)
            results_by_type[code].append((rep["overall_reliability_score"], rep["reliability_status"], rep["failure_category"]))

        print(f"[Test 6 Interleaved] Isolation verified across sequence A-B-A-C-B-C-A")
        # Verify deterministic consistency
        self.assertEqual(results_by_type["A"][0], results_by_type["A"][1])
        self.assertEqual(results_by_type["A"][1], results_by_type["A"][2])
        self.assertEqual(results_by_type["B"][0], results_by_type["B"][1])
        self.assertEqual(results_by_type["C"][0], results_by_type["C"][1])

if __name__ == "__main__":
    unittest.main()
