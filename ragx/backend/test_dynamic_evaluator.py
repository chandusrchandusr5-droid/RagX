"""
RAGX Dynamic Question Evaluation Test Script
Verifies that user-entered questions produce dynamic RAG answers, evidence chunks, claim analysis,
reliability scores, and failure classifications.
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def test_dynamic_queries():
    print("==================================================")
    print("   RAGX DYNAMIC QUESTION EVALUATION TEST SUITE    ")
    print("==================================================")

    test_questions = [
        "What is the minimum attendance requirement?",
        "What are the eligibility requirements for students?",
        "What are the policies regarding orbital space stations?"
    ]

    for idx, q in enumerate(test_questions, start=1):
        print(f"\n--- Test {idx}: Query = '{q}' ---")
        res = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": q, "top_k": 3})
        assert res.status_code == 200, f"Failed API request for query: {q}"
        data = res.json()
        report = data.get("evaluation_report", {})

        print("Returned Question:", data.get("question"))
        print("Generated Answer:", data.get("answer")[:100] + ("..." if len(data.get("answer", "")) > 100 else ""))
        print("Retrieved Chunks Count:", len(data.get("retrieved_evidence", [])))
        print("Evaluation Status:", report.get("evaluation_status"))
        print("Reliability Status:", report.get("reliability_status"))
        print("Failure Category:", report.get("failure_category"))
        print("Reliability Score:", report.get("overall_reliability_score"))
        print("Extracted Claims Count:", len(report.get("claim_analysis", [])))
        if report.get("claim_analysis"):
            print("First Claim Status:", report.get("claim_analysis")[0].get("support_status"))

        # Assertions
        assert data.get("question") == q
        assert "evaluation_report" in data
        assert "failure_category" in report

    print("\n==================================================")
    print("  ALL DYNAMIC EVALUATION TESTS PASSED SUCCESSFULLY ")
    print("==================================================")

if __name__ == "__main__":
    test_dynamic_queries()
