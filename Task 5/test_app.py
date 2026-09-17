import os
import tempfile
import unittest
import app

class QuizSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dbfile = tempfile.NamedTemporaryFile(delete=False)
        cls.dbfile.close()
        app.DB = cls.dbfile.name
        app.init_db()

    @classmethod
    def tearDownClass(cls):
        try: os.unlink(cls.dbfile.name)
        except OSError: pass

    def setUp(self):
        self.client = app.app.test_client()
        self.admin = self.login("admin", "admin123")
        self.student = self.login("student", "student123")

    def login(self, username, password):
        r=self.client.post("/api/login",json={"username":username,"password":password})
        self.assertEqual(r.status_code,200)
        return r.get_json()["token"]

    def h(self,t): return {"Authorization":"Bearer "+t}

    def test_health(self):
        self.assertEqual(self.client.get("/health").status_code,200)

    def test_docs(self):
        r=self.client.get("/api/docs")
        self.assertEqual(r.status_code,200)
        self.assertIn("/api/login", r.get_json()["endpoints"]["authentication"])

    def test_admin_can_create_quiz_and_question(self):
        r=self.client.post("/api/quizzes",headers=self.h(self.admin),json={
            "title":"Test Quiz","difficulty":"easy","negative_marking":0.25
        })
        self.assertEqual(r.status_code,201)
        qid=r.get_json()["quiz_id"]
        r=self.client.post(f"/api/quizzes/{qid}/questions",headers=self.h(self.admin),json={
            "question_text":"2 + 2 = ?","marks":1,
            "options":[
                {"option_text":"3","is_correct":False},
                {"option_text":"4","is_correct":True},
                {"option_text":"5","is_correct":False},
                {"option_text":"6","is_correct":False}
            ]
        })
        self.assertEqual(r.status_code,201)
        return qid

    def test_participant_cannot_create_quiz(self):
        r=self.client.post("/api/quizzes",headers=self.h(self.student),json={"title":"No"})
        self.assertEqual(r.status_code,403)

    def test_full_participant_flow_and_validation(self):
        r=self.client.post("/api/quizzes",headers=self.h(self.admin),json={"title":"Scoring Quiz"})
        quiz=r.get_json()["quiz_id"]
        self.client.post(f"/api/quizzes/{quiz}/questions",headers=self.h(self.admin),json={
            "question_text":"Capital of France?","marks":2,
            "options":[
                {"option_text":"Paris","is_correct":True},
                {"option_text":"Rome","is_correct":False},
                {"option_text":"Delhi","is_correct":False},
                {"option_text":"Tokyo","is_correct":False}
            ]
        })
        r=self.client.post(f"/api/quizzes/{quiz}/attempts",headers=self.h(self.student))
        self.assertEqual(r.status_code,201)
        attempt=r.get_json()["attempt_id"]

        # Invalid option must be rejected because it does not belong to the question.
        r=self.client.post(f"/api/attempts/{attempt}/submit",headers=self.h(self.student),json={
            "answers":[{"question_id":1,"option_id":999999}]
        })
        self.assertEqual(r.status_code,400)

        # Fetch actual question/option IDs, then submit correct answer.
        data=self.client.get(f"/api/quizzes/{quiz}",headers=self.h(self.student)).get_json()
        question=data["questions"][0]
        correct=[o for o in question["options"] if o["option_text"]=="Paris"][0]["id"]
        r=self.client.post(f"/api/attempts/{attempt}/submit",headers=self.h(self.student),json={
            "answers":[{"question_id":question["id"],"option_id":correct}]
        })
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.get_json()["result"]["score"],2.0)

        r=self.client.get("/api/my-results",headers=self.h(self.student))
        self.assertEqual(r.status_code,200)
        self.assertGreaterEqual(len(r.get_json()["results"]),1)

        r=self.client.get(f"/api/quizzes/{quiz}/leaderboard",headers=self.h(self.student))
        self.assertEqual(r.status_code,200)
        self.assertGreaterEqual(len(r.get_json()["leaderboard"]),1)

    def test_unauthenticated_protection(self):
        self.assertEqual(self.client.get("/api/me").status_code,401)

if __name__ == "__main__":
    unittest.main(verbosity=2)
