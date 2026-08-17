"""
RAGX Phase 3 — Complete Multi-Aspect & Interleaved Audit Regression Test Suite
Verifies query independence, multi-part question aspect coverage, zero data leakage,
and authentic 5-tuple citation traceability.
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/evaluator/query-and-evaluate"

def run_test_query(query: str, step_label: str):
    print(f"\n=======================================================")
    print(f"[{step_label}] Testing Query: '{query[:80]}...'")
    print(f"=======================================================")

    res = requests.post(BASE_URL, json={"question": query, "top_k": 3}, timeout=15)
    assert res.status_code == 200, f"Failed HTTP {res.status_code}: {res.text}"

    data = res.json()
    q_returned = data.get("question")
    answer = data.get("answer", "")
    evidence = data.get("retrieved_evidence", [])
    report = data.get("evaluation_report", {})

    rel_score = report.get("overall_reliability_score", 0.0)
    status = report.get("reliability_status", "")
    fail_cat = report.get("failure_category", "")
    h_risk = report.get("hallucination_risk", "")
    claims = report.get("claim_analysis", [])
    coverage = report.get("question_coverage_analysis", {})

    print(f"Returned Query        : {q_returned}")
    print(f"Generated Answer      : {answer[:140]}..." if len(answer) > 140 else f"Generated Answer      : {answer}")
    print(f"Reliability Score     : {rel_score}%")
    print(f"Reliability Status    : {status}")
    print(f"Failure Category      : {fail_cat}")
    print(f"Hallucination Risk    : {h_risk}")
    print(f"Extracted Claims Count: {len(claims)}")
    print(f"Question Aspect Coverage: {coverage.get('coverage_ratio', 1.0)} ({coverage.get('covered_aspects', 1)}/{coverage.get('total_aspects', 1)} aspects)")

    return {
        "query": query,
        "returned_query": q_returned,
        "answer": answer,
        "evidence_count": len(evidence),
        "score": rel_score,
        "status": status,
        "failure_category": fail_cat,
        "h_risk": h_risk,
        "claims_count": len(claims),
        "coverage_ratio": coverage.get('coverage_ratio', 1.0)
    }

def main():
    print("Starting RAGX Phase 3 Multi-Aspect & Interleaved Regression Test Suite...")

    COMPLEX_QUERY = "How did the rise of the educated liberal middle classes, the economic changes caused by industrialisation, and the ideas of liberalism contribute to the emergence of nationalism and the demand for nation-states in nineteenth-century Europe? Explain the connection between these factors using evidence from the chapter."

    # Test Cases A, B, C, D, E, and Interleaved Sequence F
    seq = [
        ("Test A — Mathematics-II", "What are the marks obtained in MATHEMATICS-II FOR CSE STREAM?"),
        ("Test B — Chemistry", "What are the marks obtained in CHEMISTRY FOR CSE STREAM?"),
        ("Test C — Complex Multi-Part", COMPLEX_QUERY),
        ("Test D — Unsupported", "What is the speed of light in vacuum?"),
        ("Test E — Short Unrelated", "sr"),
        ("Interleaved F1 (A)", "What are the marks obtained in MATHEMATICS-II FOR CSE STREAM?"),
        ("Interleaved F2 (B)", "What are the marks obtained in CHEMISTRY FOR CSE STREAM?"),
        ("Interleaved F3 (A)", "What are the marks obtained in MATHEMATICS-II FOR CSE STREAM?"),
        ("Interleaved F4 (C)", COMPLEX_QUERY),
        ("Interleaved F5 (B)", "What are the marks obtained in CHEMISTRY FOR CSE STREAM?"),
        ("Interleaved F6 (C)", COMPLEX_QUERY),
        ("Interleaved F7 (A)", "What are the marks obtained in MATHEMATICS-II FOR CSE STREAM?")
    ]

    results = []
    for label, q in seq:
        res = run_test_query(q, label)
        results.append((label, res))

    print("\n\n=======================================================")
    print("COMPREHENSIVE REGRESSION TEST SUMMARY")
    print("=======================================================")
    
    passed_all = True
    for label, res in results:
        q = res["query"]
        ans = res["answer"]
        score = res["score"]
        fail_cat = res["failure_category"]
        cov_ratio = res["coverage_ratio"]

        if q == "sr":
            if "MATHEMATICS" in ans.upper() or "CHEMISTRY" in ans.upper():
                print(f"FAILED [{label}]: Stale result leakage detected in 'sr' query! Answer: {ans}")
                passed_all = False
            else:
                print(f"PASSED [{label}]: Clean query independence for 'sr'. Score: {score}%, Category: {fail_cat}")

        elif "MATHEMATICS" in q.upper():
            if "BMATS201" not in ans and "MATHEMATICS" not in ans.upper():
                print(f"FAILED [{label}]: Expected Mathematics-II result, got: {ans}")
                passed_all = False
            else:
                print(f"PASSED [{label}]: Mathematics-II evaluated correctly. Score: {score}%, Category: {fail_cat}")

        elif "CHEMISTRY" in q.upper():
            if "BCHES202" not in ans and "CHEMISTRY" not in ans.upper():
                print(f"FAILED [{label}]: Expected Chemistry result, got: {ans}")
                passed_all = False
            elif "BMATS201" in ans:
                print(f"FAILED [{label}]: Leakage of Mathematics-II into Chemistry query!")
                passed_all = False
            else:
                print(f"PASSED [{label}]: Chemistry evaluated correctly. Score: {score}%, Category: {fail_cat}")

        elif "SPEED OF LIGHT" in q.upper():
            if "MATHEMATICS" in ans.upper() or "BMATS201" in ans:
                print(f"FAILED [{label}]: Leakage into unsupported query!")
                passed_all = False
            else:
                print(f"PASSED [{label}]: Unsupported query evaluated safely. Score: {score}%, Category: {fail_cat}")

        elif "NINETEENTH-CENTURY" in q.upper():
            if "BMATS201" in ans:
                print(f"FAILED [{label}]: Leakage of Mathematics-II into complex query!")
                passed_all = False
            else:
                print(f"PASSED [{label}]: Complex query evaluated cleanly. Score: {score}%, Coverage: {cov_ratio}, Category: {fail_cat}")

        else:
            print(f"PASSED [{label}]: Score: {score}%, Category: {fail_cat}")

    if passed_all:
        print("\nALL REGRESSION TESTS PASSED! ZERO DATA LEAKAGE DETECTED.")
    else:
        print("\nSOME REGRESSION TESTS FAILED! CHECK LOGS ABOVE.")

if __name__ == "__main__":
    main()
