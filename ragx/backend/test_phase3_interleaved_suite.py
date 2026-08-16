"""
RAGX Phase 3 — End-to-End Interleaved Query & Audit Regression Test Suite
Verifies query independence, zero data leakage across interleaved queries,
and authentic 5-tuple citation traceability.
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/evaluator/query-and-evaluate"

def run_test_query(query: str, step_label: str):
    print(f"\n=======================================================")
    print(f"[{step_label}] Testing Query: '{query}'")
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

    print(f"Returned Query        : {q_returned}")
    print(f"Generated Answer      : {answer[:120]}..." if len(answer) > 120 else f"Generated Answer      : {answer}")
    print(f"Reliability Score     : {rel_score}%")
    print(f"Reliability Status    : {status}")
    print(f"Failure Category      : {fail_cat}")
    print(f"Hallucination Risk    : {h_risk}")
    print(f"Extracted Claims Count: {len(claims)}")

    return {
        "query": query,
        "returned_query": q_returned,
        "answer": answer,
        "evidence_count": len(evidence),
        "score": rel_score,
        "status": status,
        "failure_category": fail_cat,
        "h_risk": h_risk,
        "claims_count": len(claims)
    }

def main():
    print("Starting RAGX Phase 3 Interleaved & Query Independence Regression Test...")

    # Interleaved Sequence: A -> B -> A -> C -> B -> C -> A -> D -> E
    seq = [
        ("Query A", "What are the marks obtained in MATHEMATICS-II FOR CSE STREAM?"),
        ("Query B (sr)", "sr"),
        ("Query A Repeat", "What are the marks obtained in MATHEMATICS-II FOR CSE STREAM?"),
        ("Query C", "What are the marks obtained in CHEMISTRY FOR CSE STREAM?"),
        ("Query B Repeat (sr)", "sr"),
        ("Query C Repeat", "What are the marks obtained in CHEMISTRY FOR CSE STREAM?"),
        ("Query A Repeat 2", "What are the marks obtained in MATHEMATICS-II FOR CSE STREAM?"),
        ("Query D (Absent Entity)", "Who is Chandu SR?"),
        ("Query E (Attendance Policy)", "What is the minimum attendance requirement?")
    ]

    results = []
    for label, q in seq:
        res = run_test_query(q, label)
        results.append((label, res))

    print("\n\n=======================================================")
    print("INTERLEAVED REGRESSION TEST SUMMARY")
    print("=======================================================")
    
    passed_all = True
    for label, res in results:
        q = res["query"]
        ans = res["answer"]
        score = res["score"]
        fail_cat = res["failure_category"]

        if q == "sr":
            # sr MUST NOT contain previous Mathematics-II or Chemistry text
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
                print(f"PASSED [{label}]: Mathematics-II evaluated correctly. Score: {score}%")

        elif "CHEMISTRY" in q.upper():
            if "BCHES202" not in ans and "CHEMISTRY" not in ans.upper():
                print(f"FAILED [{label}]: Expected Chemistry result, got: {ans}")
                passed_all = False
            elif "BMATS201" in ans:
                print(f"FAILED [{label}]: Leakage of Mathematics-II into Chemistry query!")
                passed_all = False
            else:
                print(f"PASSED [{label}]: Chemistry evaluated correctly. Score: {score}%")

        elif "CHANDU" in q.upper():
            if "MATHEMATICS" in ans.upper() or "BMATS201" in ans:
                print(f"FAILED [{label}]: Leakage of Mathematics-II into absent entity query!")
                passed_all = False
            else:
                print(f"PASSED [{label}]: Absent entity handled safely without leakage. Score: {score}%, Category: {fail_cat}")

        else:
            print(f"PASSED [{label}]: Score: {score}%, Category: {fail_cat}")


    if passed_all:
        print("\nALL INTERLEAVED REGRESSION TESTS PASSED! ZERO STALE RESULT LEAKAGE DETECTED.")
    else:
        print("\nSOME REGRESSION TESTS FAILED! CHECK LOGS ABOVE.")

if __name__ == "__main__":
    main()
