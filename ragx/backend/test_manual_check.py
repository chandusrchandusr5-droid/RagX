"""
RAGX Local Manual Verification Script
Tests additional arbitrary questions, evaluator analytics, and Nova Assistant API.
"""
import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000/api"

def run_manual_verification():
    print("==================================================")
    print("     RAGX LOCAL MANUAL VERIFICATION & DIAGNOSTICS")
    print("==================================================")

    queries = [
        "What is the student's USN and Name?",
        "What are the internal marks in APPLIED CHEMISTRY FOR CSE STREAM?",
        "What is the result status of BMATS201 MATHEMATICS-II?",
        "Who is the Chancellor of the University?"
    ]

    for q in queries:
        print(f"\n--------------------------------------------------")
        print(f" Query: \"{q}\"")
        print(f"--------------------------------------------------")
        res = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": q})
        if res.status_code == 200:
            data = res.json()
            rep = data.get("evaluation_report", {})
            ans = rep.get("generated_answer", "")
            score = rep.get("overall_reliability_score", 0.0)
            risk = rep.get("hallucination_risk", "")
            print(f" Answer: {ans}")
            print(f" Score: {score}% | Risk: {risk}")
        else:
            print(f" Error {res.status_code}: {res.text}")

    print("\n--------------------------------------------------")
    print(" Testing /evaluator/analytics Endpoint")
    print("--------------------------------------------------")
    res_analytics = requests.get(f"{BASE_URL}/evaluator/analytics")
    if res_analytics.status_code == 200:
        analytics = res_analytics.json()
        print(f" Total Evaluations Logged: {analytics.get('total_evaluations')}")
        print(f" Average Reliability Score: {analytics.get('average_reliability_score')}%")
        print(f" Reliability Distribution: {analytics.get('reliability_distribution')}")
    else:
        print(f" Analytics Error {res_analytics.status_code}")

    print("\n--------------------------------------------------")
    print(" Testing NOVA AI Copilot Assistant /nova/chat")
    print("--------------------------------------------------")
    nova_res = requests.post(f"{BASE_URL}/nova/chat", json={"message": "Can you explain why Math-II score is low?"})
    if nova_res.status_code == 200:
        nova_data = nova_res.json()
        print(f" Nova Response:\n {nova_data.get('response')}")
    else:
        print(f" Nova Chat Error {nova_res.status_code}")

if __name__ == "__main__":
    run_manual_verification()
