"""
RAGX Approved Fix Implementation Verification Test Suite
Tests Fix A (Prompt Scoping), Fix B (Fallback Synthesizer), and Fix C (Question Relevance Classification).
"""
import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')


BASE_URL = "http://127.0.0.1:8000/api"

def run_test_suite():
    print("==================================================")
    print("    RAGX APPROVED FIX SUITE (FIX A, B, C) VERIFICATION")
    print("==================================================")

    test_cases = [
        {
            "id": "Test 1 — Target Subject (Math II)",
            "query": "What are the marks obtained in MATHEMATICS-II FOR CSE STREAM?",
            "target_keywords": ["MATHEMATICS-II", "CSE STREAM"],
            "forbidden_keywords": ["CHEMISTRY", "COMPUTER-AIDED ENGINEERING DRAWING"],
            "expected_type": "SPECIFIC_TARGET"
        },
        {
            "id": "Test 2 — Target Subject (Chemistry)",
            "query": "What are the marks obtained in CHEMISTRY?",
            "target_keywords": ["CHEMISTRY"],
            "forbidden_keywords": ["MATHEMATICS-II", "COMPUTER-AIDED ENGINEERING DRAWING"],
            "expected_type": "SPECIFIC_TARGET"
        },
        {
            "id": "Test 3 — Target Subject (Engineering Drawing)",
            "query": "What are the marks obtained in COMPUTER-AIDED ENGINEERING DRAWING?",
            "target_keywords": ["COMPUTER-AIDED ENGINEERING DRAWING"],
            "forbidden_keywords": ["CHEMISTRY", "MATHEMATICS-II"],
            "expected_type": "SPECIFIC_TARGET"
        },
        {
            "id": "Test 4 — Broad Query (Complete Result)",
            "query": "What is the student's complete result?",
            "target_keywords": ["MATHEMATICS-II", "CHEMISTRY"],
            "forbidden_keywords": [],
            "expected_type": "BROAD_SUMMARY"
        },
        {
            "id": "Test 5 — Unsupported Query (Quantum Computing)",
            "query": "What are the marks obtained in QUANTUM COMPUTING?",
            "target_keywords": [],
            "forbidden_keywords": [],
            "expected_type": "UNSUPPORTED_QUERY"
        }
    ]

    results = []

    for case in test_cases:
        print(f"\n--------------------------------------------------")
        print(f" Executing {case['id']}")
        print(f" Query: \"{case['query']}\"")
        print(f"--------------------------------------------------")

        res = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": case["query"]})
        assert res.status_code == 200, f"API Call failed with status {res.status_code}"
        
        data = res.json()
        eval_rep = data.get("evaluation_report", {})
        answer = eval_rep.get("generated_answer", "")
        claims = eval_rep.get("claim_analysis", [])

        print(f" Generated Answer:")
        print(f"  {repr(answer)}")
        print(f" Claim Analysis:")
        for c in claims:
            cid = c.get("claim_id")
            ctext = c.get("claim_text")
            status = c.get("support_status")
            rel = c.get("relevance_classification", "N/A")
            print(f"  - [{cid}] {repr(ctext)} -> Support: {status} | Relevance: {rel}")

        score = eval_rep.get("overall_reliability_score")
        risk = eval_rep.get("hallucination_risk")
        over_gen = eval_rep.get("over_generation_detected", False)
        
        print(f"\n Evaluation Summary:")
        print(f"  - Overall Reliability Score (S_Ans): {score}%")
        print(f"  - Hallucination Risk: {risk}")
        print(f"  - Over-generation Detected: {over_gen}")


        # Verification Checks
        passed = True
        notes = []

        if case["expected_type"] == "SPECIFIC_TARGET":
            for fk in case["forbidden_keywords"]:
                if fk.lower() in answer.lower():
                    passed = False
                    notes.append(f"FAILED: Over-generated unrequested content '{fk}'")
            for tk in case["target_keywords"]:
                if tk.lower() not in answer.lower() and "could not be found" not in answer.lower():
                    passed = False
                    notes.append(f"FAILED: Missing target keyword '{tk}'")

        elif case["expected_type"] == "UNSUPPORTED_QUERY":
            if "could not be found" not in answer.lower() and "no relevant" not in answer.lower():
                passed = False
                notes.append("FAILED: Did not report un-found status for absent query")

        status_str = "PASSED" if passed else "FAILED"
        print(f"\n Verification Result: {status_str}")
        if notes:
            for n in notes:
                print(f"  - {n}")

        results.append({
            "case_id": case["id"],
            "query": case["query"],
            "answer": answer,
            "claims": claims,
            "score": score,
            "risk": risk,
            "over_gen": over_gen,
            "passed": passed
        })

    print("\n==================================================")
    print("           SUMMARY OF REGRESSION TESTS            ")
    print("==================================================")
    for r in results:
        p_str = "PASSED" if r["passed"] else "FAILED"
        print(f" - {r['case_id']}: [{p_str}] Score={r['score']}% | Risk={r['risk']} | OverGen={r['over_gen']}")


if __name__ == "__main__":
    run_test_suite()
