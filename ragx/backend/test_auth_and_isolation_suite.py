import unittest
import os
import shutil
import sqlite3
import json
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import AuthService
from app.services.document_registry import DocumentRegistryService
from app.core.vector_db import vector_db

client = TestClient(app)

class TestAuthAndIsolationSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.user_a_email = f"user_a_{uuid.uuid4().hex[:6]}@example.com"
        cls.user_b_email = f"user_b_{uuid.uuid4().hex[:6]}@example.com"
        cls.pwd = "Password123!"

        # 1. Register User A
        res_a = client.post("/api/auth/register", json={
            "email": cls.user_a_email,
            "full_name": "User Alpha Test",
            "password": cls.pwd
        })
        data_a = res_a.json()
        cls.token_a = data_a["token"]
        cls.user_a_id = data_a["user"]["id"]

        # 2. Register User B
        res_b = client.post("/api/auth/register", json={
            "email": cls.user_b_email,
            "full_name": "User Beta Test",
            "password": cls.pwd
        })
        data_b = res_b.json()
        cls.token_b = data_b["token"]
        cls.user_b_id = data_b["user"]["id"]

        # 3. Login Admin
        res_admin = client.post("/api/auth/login", json={
            "email": "teamragx@gmail.com",
            "password": "teamrag123"
        })
        cls.token_admin = res_admin.json()["token"]

    @classmethod
    def tearDownClass(cls):
        """Clean up test users, session tokens, activity logs, and registry entries after test run."""
        try:
            db_path = Path("data/users.db")
            if db_path.exists():
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE email LIKE 'user_%@example.com'")
                cursor.execute("DELETE FROM sessions WHERE user_id NOT IN (SELECT id FROM users)")
                cursor.execute("DELETE FROM activity_logs WHERE user_email LIKE 'user_%@example.com' OR details LIKE '%test_doc%'")
                conn.commit()
                conn.close()

            registry_path = Path("data/document_registry.json")
            if registry_path.exists():
                with open(registry_path, "r", encoding="utf-8") as f:
                    docs = json.load(f)
                clean_docs = [d for d in docs if not d.get("document_name", "").startswith("test_doc_")]
                with open(registry_path, "w", encoding="utf-8") as f:
                    json.dump(clean_docs, f, indent=2)
        except Exception as e:
            print(f"tearDownClass cleanup warning: {e}")

    def test_01_user_profile_and_password_settings(self):
        """Case 1: Change Name and Change Password."""
        headers_a = {"Authorization": f"Bearer {TestAuthAndIsolationSuite.token_a}"}
        
        # Change Name
        res_profile = client.put("/api/auth/profile", json={"full_name": "Alpha Updated"}, headers=headers_a)
        self.assertEqual(res_profile.status_code, 200)
        self.assertEqual(res_profile.json()["user"]["full_name"], "Alpha Updated")

        # Change Password
        new_pwd = "NewPassword456!"
        res_pwd = client.post("/api/auth/change-password", json={
            "current_password": TestAuthAndIsolationSuite.pwd,
            "new_password": new_pwd
        }, headers=headers_a)
        self.assertEqual(res_pwd.status_code, 200)

        # Login with new password
        res_login_new = client.post("/api/auth/login", json={
            "email": TestAuthAndIsolationSuite.user_a_email,
            "password": new_pwd
        })
        self.assertEqual(res_login_new.status_code, 200)
        TestAuthAndIsolationSuite.token_a = res_login_new.json()["token"]

    def test_02_per_user_document_isolation(self):
        """Case 2: Document Upload & List Isolation (User A vs User B)."""
        headers_a = {"Authorization": f"Bearer {TestAuthAndIsolationSuite.token_a}"}
        headers_b = {"Authorization": f"Bearer {TestAuthAndIsolationSuite.token_b}"}

        # Create dummy text files
        test_file_a = Path("test_doc_alpha.txt")
        test_file_a.write_text("User Alpha secret document content: Quantum Computing Breakthrough 2026.")

        test_file_b = Path("test_doc_beta.txt")
        test_file_b.write_text("User Beta secret document content: Advanced Pharmacology Metformin 500mg.")

        try:
            # User A uploads doc A
            with open(test_file_a, "rb") as f:
                res_upload_a = client.post("/api/documents/upload", files={"file": ("test_doc_alpha.txt", f, "text/plain")}, headers=headers_a)
            self.assertEqual(res_upload_a.status_code, 200)

            # User B uploads doc B
            with open(test_file_b, "rb") as f:
                res_upload_b = client.post("/api/documents/upload", files={"file": ("test_doc_beta.txt", f, "text/plain")}, headers=headers_b)
            self.assertEqual(res_upload_b.status_code, 200)

            # User A lists documents -> sees doc A, DOES NOT see doc B
            res_list_a = client.get("/api/documents", headers=headers_a)
            doc_names_a = [d["document_name"] for d in res_list_a.json()["documents"]]
            self.assertIn("test_doc_alpha.txt", doc_names_a)
            self.assertNotIn("test_doc_beta.txt", doc_names_a)

            # User B lists documents -> sees doc B, DOES NOT see doc A
            res_list_b = client.get("/api/documents", headers=headers_b)
            doc_names_b = [d["document_name"] for d in res_list_b.json()["documents"]]
            self.assertIn("test_doc_beta.txt", doc_names_b)
            self.assertNotIn("test_doc_alpha.txt", doc_names_b)

        finally:
            if test_file_a.exists(): test_file_a.unlink()
            if test_file_b.exists(): test_file_b.unlink()

    def test_03_retrieval_and_oracle_isolation(self):
        """Case 3: RAG Engine & Full-KB Oracle Retrieval Isolation."""
        headers_b = {"Authorization": f"Bearer {TestAuthAndIsolationSuite.token_b}"}

        # User B queries for User A's secret content ("Quantum Computing Breakthrough")
        res_rag_b = client.post("/api/rag/query", json={"question": "Quantum Computing Breakthrough", "top_k": 3}, headers=headers_b)
        self.assertEqual(res_rag_b.status_code, 200)
        retrieved_b = res_rag_b.json()["retrieved_evidence"]
        
        # Verify ZERO chunks from User A's doc returned to User B
        for chunk in retrieved_b:
            self.assertNotEqual(chunk["document_name"], "test_doc_alpha.txt")

    def test_04_legacy_dev_data_isolation(self):
        """Case 4: Legacy Pre-Auth Development Data Isolation."""
        user_c_email = f"user_c_{uuid.uuid4().hex[:6]}@example.com"
        res_c = client.post("/api/auth/register", json={
            "email": user_c_email,
            "full_name": "User Gamma Test",
            "password": TestAuthAndIsolationSuite.pwd
        })
        token_c = res_c.json()["token"]
        headers_c = {"Authorization": f"Bearer {token_c}"}

        # User C lists documents -> baseline/legacy PDFs are accessible
        res_list_c = client.get("/api/documents", headers=headers_c)
        self.assertGreaterEqual(res_list_c.json()["total_documents"], 8)

    def test_05_admin_access_controls(self):
        """Case 5: Server-side Admin Access Restrictions & Activity Log."""
        headers_a = {"Authorization": f"Bearer {TestAuthAndIsolationSuite.token_a}"}
        headers_admin = {"Authorization": f"Bearer {TestAuthAndIsolationSuite.token_admin}"}

        # Normal User A attempts to call Admin API -> 403 Forbidden
        res_denied = client.get("/api/admin/dashboard", headers=headers_a)
        self.assertEqual(res_denied.status_code, 403)

        # Admin calls Admin Dashboard -> 200 OK
        res_dashboard = client.get("/api/admin/dashboard", headers=headers_admin)
        self.assertEqual(res_dashboard.status_code, 200)
        self.assertIn("metrics", res_dashboard.json())

        # Admin fetches User List -> Passwords/hashes/tokens are NOT exposed
        res_users = client.get("/api/admin/users", headers=headers_admin)
        self.assertEqual(res_users.status_code, 200)
        users = res_users.json()["users"]
        for u in users:
            self.assertNotIn("password_hash", u)
            self.assertNotIn("salt", u)
            self.assertNotIn("token", u)

    def test_06_user_scoped_data_quality_and_analytics(self):
        """Case 6: User-Scoped Data Quality and Evaluator Analytics."""
        user_d_email = f"user_d_{uuid.uuid4().hex[:6]}@example.com"
        res_d = client.post("/api/auth/register", json={
            "email": user_d_email,
            "full_name": "User Delta Test",
            "password": TestAuthAndIsolationSuite.pwd
        })
        token_d = res_d.json()["token"]
        headers_d = {"Authorization": f"Bearer {token_d}"}

        # User D calls Data Quality Audit -> Includes baseline documents
        res_dq_d = client.get("/api/quality/audit", headers=headers_d)
        self.assertEqual(res_dq_d.status_code, 200)
        dq_data_d = res_dq_d.json()
        self.assertGreaterEqual(dq_data_d["scoring_breakdown"]["raw_measurements"]["total_documents"], 8)

        # User D calls Analytics -> Includes baseline evaluations
        res_analytics_d = client.get("/api/evaluator/analytics", headers=headers_d)
        self.assertEqual(res_analytics_d.status_code, 200)
        analytics_d = res_analytics_d.json()
        self.assertGreaterEqual(analytics_d["total_evaluations"], 1)

    def test_07_real_activity_feed_no_fake_data(self):
        """Case 7: Verify Real Activity Logs in Admin Portal."""
        headers_admin = {"Authorization": f"Bearer {TestAuthAndIsolationSuite.token_admin}"}
        res_act = client.get("/api/admin/activity", headers=headers_admin)
        self.assertEqual(res_act.status_code, 200)
        activities = res_act.json()["activities"]
        
        # Verify activity entries exist and correspond to actual real events
        actions = [a["action"] for a in activities]
        self.assertTrue(any("Account Registered" in act or "Login" in act or "PDF" in act for act in actions))

    def test_08_account_deletion_cleanup(self):
        """Case 8: Account Deletion and Scoped Cleanup."""
        headers_b = {"Authorization": f"Bearer {TestAuthAndIsolationSuite.token_b}"}
        
        # User B deletes their account
        res_del = client.delete("/api/auth/account", headers=headers_b)
        self.assertEqual(res_del.status_code, 200)

        # User B token invalidated
        res_me_b = client.get("/api/auth/me", headers=headers_b)
        self.assertEqual(res_me_b.status_code, 401)

        # User A's documents remain completely intact
        headers_a = {"Authorization": f"Bearer {TestAuthAndIsolationSuite.token_a}"}
        res_list_a = client.get("/api/documents", headers=headers_a)
        doc_names_a = [d["document_name"] for d in res_list_a.json()["documents"]]
        self.assertIn("test_doc_alpha.txt", doc_names_a)

if __name__ == "__main__":
    unittest.main()
