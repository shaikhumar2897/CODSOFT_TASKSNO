from flask import Flask, request, jsonify, session, render_template_string, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, secrets, datetime, random, functools, os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
DB = os.path.join(os.path.dirname(__file__), "quiz.db")

# -------------------- DATABASE --------------------
SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin','participant')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quizzes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    difficulty TEXT NOT NULL DEFAULT 'medium'
        CHECK(difficulty IN ('easy','medium','hard')),
    negative_marking REAL NOT NULL DEFAULT 0,
    time_limit INTEGER NOT NULL DEFAULT 0,
    created_by INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    marks REAL NOT NULL DEFAULT 1,
    FOREIGN KEY(quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    option_text TEXT NOT NULL,
    is_correct INTEGER NOT NULL DEFAULT 0 CHECK(is_correct IN (0,1)),
    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    submitted_at TEXT,
    score REAL NOT NULL DEFAULT 0,
    total_marks REAL NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    wrong_count INTEGER NOT NULL DEFAULT 0,
    unanswered_count INTEGER NOT NULL DEFAULT 0,
    percentage REAL NOT NULL DEFAULT 0,
    passed INTEGER NOT NULL DEFAULT 0,
    UNIQUE(quiz_id, user_id, id),
    FOREIGN KEY(quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    option_id INTEGER,
    is_correct INTEGER NOT NULL DEFAULT 0,
    marks_awarded REAL NOT NULL DEFAULT 0,
    FOREIGN KEY(attempt_id) REFERENCES attempts(id) ON DELETE CASCADE,
    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY(option_id) REFERENCES options(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS api_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_=None):
    conn = g.pop("db", None)
    if conn:
        conn.close()

def seed_ready_made_quizzes(conn, admin_id):
    """Create five ready-made quizzes the first time the database has no quizzes."""
    if conn.execute("SELECT COUNT(*) FROM quizzes").fetchone()[0] > 0:
        return

    quizzes = [
        {
            "title": "Python Programming",
            "description": "Test your knowledge of Python basics, syntax, data types and functions.",
            "difficulty": "easy",
            "negative": 0.25,
            "time": 10,
            "questions": [
                ("Which keyword is used to define a function in Python?", ["func", "def", "function", "define"], 1),
                ("Which of these is a Python list?", ["{1, 2, 3}", "(1, 2, 3)", "[1, 2, 3]", "<1, 2, 3>"], 2),
                ("What is the output of 2 ** 3?", ["6", "8", "9", "12"], 1),
                ("Which data type stores True or False?", ["int", "str", "bool", "float"], 2),
                ("Which function displays output on the screen?", ["input()", "print()", "show()", "display()"], 1),
            ]
        },
        {
            "title": "C Programming",
            "description": "Practice fundamental C programming concepts, operators, loops and arrays.",
            "difficulty": "easy",
            "negative": 0.25,
            "time": 10,
            "questions": [
                ("Which header file is commonly used for printf() and scanf()?", ["math.h", "string.h", "stdio.h", "stdlib.h"], 2),
                ("Which symbol ends a C statement?", [".", ";", ":", ","], 1),
                ("Which loop is guaranteed to execute at least once?", ["for", "while", "do-while", "nested for"], 2),
                ("Array indexing in C normally starts at:", ["0", "1", "-1", "2"], 0),
                ("Which operator is used to get the address of a variable?", ["*", "&", "%", "#"], 1),
            ]
        },
        {
            "title": "Web Development",
            "description": "Check your understanding of HTML, CSS, JavaScript and basic web concepts.",
            "difficulty": "medium",
            "negative": 0.25,
            "time": 10,
            "questions": [
                ("What does HTML stand for?", ["Hyper Text Markup Language", "High Tech Modern Language", "Hyperlink Text Management Language", "Home Tool Markup Language"], 0),
                ("Which language is primarily used to style web pages?", ["HTML", "CSS", "SQL", "Python"], 1),
                ("Which HTML tag creates a hyperlink?", ["<link>", "<a>", "<href>", "<url>"], 1),
                ("Which language adds interactivity to web pages?", ["JavaScript", "SQL", "XML", "CSS"], 0),
                ("Which CSS property changes text color?", ["font-style", "background", "color", "text-size"], 2),
            ]
        },
        {
            "title": "DBMS & SQL",
            "description": "Test database fundamentals, SQL queries, keys and relational concepts.",
            "difficulty": "medium",
            "negative": 0.25,
            "time": 12,
            "questions": [
                ("What does DBMS stand for?", ["Data Backup Management System", "Database Management System", "Database Memory System", "Digital Base Management Service"], 1),
                ("Which SQL command is used to retrieve data?", ["GET", "SELECT", "FETCHDB", "OPEN"], 1),
                ("Which key uniquely identifies a row in a table?", ["Foreign key", "Primary key", "Candidate value", "Index key"], 1),
                ("Which SQL command adds a new row?", ["ADD", "INSERT", "UPDATE", "CREATE"], 1),
                ("Which SQL clause filters rows?", ["ORDER BY", "GROUP BY", "WHERE", "SORT"], 2),
            ]
        },
        {
            "title": "Computer Fundamentals",
            "description": "A general quiz covering operating systems, hardware, networking and computer basics.",
            "difficulty": "medium",
            "negative": 0.25,
            "time": 12,
            "questions": [
                ("Which component is known as the brain of the computer?", ["RAM", "CPU", "Hard disk", "Monitor"], 1),
                ("Which memory is volatile?", ["ROM", "RAM", "SSD", "DVD"], 1),
                ("What does OS stand for?", ["Open Software", "Operating System", "Online Service", "Output System"], 1),
                ("Which device connects a computer to a network?", ["NIC", "ALU", "CPU", "UPS"], 0),
                ("Which number system uses only 0 and 1?", ["Decimal", "Octal", "Binary", "Hexadecimal"], 2),
            ]
        },
    ]

    for quiz in quizzes:
        cur = conn.execute(
            """INSERT INTO quizzes(title,description,difficulty,negative_marking,time_limit,created_by,created_at)
               VALUES(?,?,?,?,?,?,?)""",
            (quiz["title"], quiz["description"], quiz["difficulty"],
             quiz["negative"], quiz["time"], admin_id, utcnow())
        )
        quiz_id = cur.lastrowid
        for question_text, option_texts, correct_index in quiz["questions"]:
            qcur = conn.execute(
                "INSERT INTO questions(quiz_id,question_text,marks) VALUES(?,?,?)",
                (quiz_id, question_text, 1)
            )
            question_id = qcur.lastrowid
            for index, option_text in enumerate(option_texts):
                conn.execute(
                    "INSERT INTO options(question_id,option_text,is_correct) VALUES(?,?,?)",
                    (question_id, option_text, 1 if index == correct_index else 0)
                )


def init_db():
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)

    # Always make sure the demo admin and participant exist, even if the
    # database already contains another registered user.
    now = utcnow()
    admin = conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if admin is None:
        cur = conn.execute(
            "INSERT INTO users(username,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
            ("admin", "admin@example.com", generate_password_hash("admin123"), "admin", now)
        )
        admin_id = cur.lastrowid
    else:
        admin_id = admin[0]

    student = conn.execute("SELECT id FROM users WHERE username='student'").fetchone()
    if student is None:
        conn.execute(
            "INSERT INTO users(username,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
            ("student", "student@example.com", generate_password_hash("student123"), "participant", now)
        )

    # Seed exactly five complete quizzes only when there are no quizzes yet.
    seed_ready_made_quizzes(conn, admin_id)
    conn.commit()
    conn.close()

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def json_error(message, status=400):
    return jsonify({"success": False, "error": message}), status

def get_user_from_token():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    if not token:
        return None
    return db().execute("""
        SELECT u.* FROM users u
        JOIN api_tokens t ON t.user_id=u.id
        WHERE t.token=?
    """, (token,)).fetchone()

def auth_required(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_user_from_token()
        if not user:
            return json_error("Authentication required. Login and send Authorization: Bearer <token>.", 401)
        g.current_user = user
        return fn(*args, **kwargs)
    return wrapper

def role_required(role):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_user_from_token()
            if not user:
                return json_error("Authentication required.", 401)
            if user["role"] != role:
                return json_error(f"{role} access required.", 403)
            g.current_user = user
            return fn(*args, **kwargs)
        return wrapper
    return deco

def validate_json(required=()):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, json_error("Request body must be valid JSON.", 400)
    missing = [x for x in required if x not in data]
    if missing:
        return None, json_error("Missing fields: " + ", ".join(missing), 400)
    return data, None

def quiz_dict(q):
    return {
        "id": q["id"], "title": q["title"], "description": q["description"],
        "difficulty": q["difficulty"], "negative_marking": q["negative_marking"],
        "time_limit": q["time_limit"], "created_at": q["created_at"],
        "created_by": q["created_by"]
    }

# -------------------- AUTH --------------------
@app.post("/api/register")
def register():
    data, err = validate_json(("username", "email", "password"))
    if err: return err
    username = str(data["username"]).strip()
    email = str(data["email"]).strip().lower()
    password = str(data["password"])
    if len(username) < 3 or len(username) > 30:
        return json_error("Username must be 3-30 characters.")
    if "@" not in email:
        return json_error("Enter a valid email address.")
    if len(password) < 6:
        return json_error("Password must contain at least 6 characters.")
    try:
        cur = db().execute("""
            INSERT INTO users(username,email,password_hash,role,created_at)
            VALUES(?,?,?,?,?)
        """, (username, email, generate_password_hash(password), "participant", utcnow()))
        db().commit()
    except sqlite3.IntegrityError:
        return json_error("Username or email already exists.", 409)
    return jsonify({"success": True, "message": "Registration successful.", "user_id": cur.lastrowid}), 201

@app.post("/api/login")
def login():
    data, err = validate_json(("username", "password"))
    if err: return err
    username = str(data["username"]).strip()
    user = db().execute("SELECT * FROM users WHERE username=? OR email=?", (username, username.lower())).fetchone()
    if not user or not check_password_hash(user["password_hash"], str(data["password"])):
        return json_error("Invalid username/email or password.", 401)
    token = secrets.token_urlsafe(40)
    db().execute("INSERT INTO api_tokens(user_id,token,created_at) VALUES(?,?,?)", (user["id"], token, utcnow()))
    db().commit()
    return jsonify({
        "success": True, "token": token,
        "user": {"id": user["id"], "username": user["username"], "email": user["email"], "role": user["role"]}
    })

@app.post("/api/logout")
@auth_required
def logout():
    auth = request.headers.get("Authorization", "")
    token = auth.split(" ", 1)[1].strip()
    db().execute("DELETE FROM api_tokens WHERE token=?", (token,))
    db().commit()
    return jsonify({"success": True, "message": "Logged out."})

@app.get("/api/me")
@auth_required
def me():
    u = g.current_user
    return jsonify({"success": True, "user": dict(u) | {"password_hash": None}})

# -------------------- QUIZZES --------------------
@app.get("/api/quizzes")
def list_quizzes():
    rows = db().execute("SELECT * FROM quizzes ORDER BY id DESC").fetchall()
    return jsonify({"success": True, "quizzes": [quiz_dict(q) for q in rows]})

@app.get("/api/quizzes/<int:quiz_id>")
@auth_required
def get_quiz(quiz_id):
    q = db().execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,)).fetchone()
    if not q:
        return json_error("Quiz not found.", 404)
    questions = []
    for question in db().execute("SELECT * FROM questions WHERE quiz_id=? ORDER BY id", (quiz_id,)).fetchall():
        opts = db().execute(
            "SELECT id, option_text FROM options WHERE question_id=? ORDER BY id",
            (question["id"],)
        ).fetchall()
        questions.append({
            "id": question["id"], "question_text": question["question_text"],
            "marks": question["marks"],
            "options": [dict(o) for o in opts]
        })
    return jsonify({"success": True, "quiz": quiz_dict(q), "questions": questions})

@app.post("/api/quizzes")
@role_required("admin")
def create_quiz():
    data, err = validate_json(("title",))
    if err: return err
    title = str(data["title"]).strip()
    description = str(data.get("description", "")).strip()
    difficulty = str(data.get("difficulty", "medium")).lower()
    try:
        negative = float(data.get("negative_marking", 0))
        time_limit = int(data.get("time_limit", 0))
    except (TypeError, ValueError):
        return json_error("negative_marking must be a number and time_limit must be an integer.")
    if not title: return json_error("Quiz title cannot be empty.")
    if difficulty not in ("easy", "medium", "hard"):
        return json_error("Difficulty must be easy, medium or hard.")
    if negative < 0 or negative > 100:
        return json_error("negative_marking must be between 0 and 100.")
    if time_limit < 0:
        return json_error("time_limit cannot be negative.")
    cur = db().execute("""
        INSERT INTO quizzes(title,description,difficulty,negative_marking,time_limit,created_by,created_at)
        VALUES(?,?,?,?,?,?,?)
    """, (title, description, difficulty, negative, time_limit, g.current_user["id"], utcnow()))
    db().commit()
    return jsonify({"success": True, "quiz_id": cur.lastrowid}), 201

@app.put("/api/quizzes/<int:quiz_id>")
@role_required("admin")
def update_quiz(quiz_id):
    q = db().execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,)).fetchone()
    if not q: return json_error("Quiz not found.", 404)
    data, err = validate_json()
    if err: return err
    title = str(data.get("title", q["title"])).strip()
    description = str(data.get("description", q["description"])).strip()
    difficulty = str(data.get("difficulty", q["difficulty"])).lower()
    negative = data.get("negative_marking", q["negative_marking"])
    time_limit = data.get("time_limit", q["time_limit"])
    try:
        negative, time_limit = float(negative), int(time_limit)
    except (TypeError, ValueError):
        return json_error("Invalid negative_marking or time_limit.")
    if not title or difficulty not in ("easy","medium","hard") or negative < 0 or time_limit < 0:
        return json_error("Invalid quiz data.")
    db().execute("""UPDATE quizzes SET title=?,description=?,difficulty=?,negative_marking=?,time_limit=? WHERE id=?""",
                 (title, description, difficulty, negative, time_limit, quiz_id))
    db().commit()
    return jsonify({"success": True, "message": "Quiz updated."})

@app.delete("/api/quizzes/<int:quiz_id>")
@role_required("admin")
def delete_quiz(quiz_id):
    cur = db().execute("DELETE FROM quizzes WHERE id=?", (quiz_id,))
    db().commit()
    if cur.rowcount == 0: return json_error("Quiz not found.", 404)
    return jsonify({"success": True, "message": "Quiz deleted."})

# -------------------- QUESTION MANAGEMENT --------------------
@app.post("/api/quizzes/<int:quiz_id>/questions")
@role_required("admin")
def add_question(quiz_id):
    if not db().execute("SELECT id FROM quizzes WHERE id=?", (quiz_id,)).fetchone():
        return json_error("Quiz not found.", 404)
    data, err = validate_json(("question_text", "options"))
    if err: return err
    text = str(data["question_text"]).strip()
    options = data["options"]
    if not text: return json_error("Question text cannot be empty.")
    if not isinstance(options, list) or len(options) < 2:
        return json_error("At least 2 options are required.")
    try: marks = float(data.get("marks", 1))
    except (TypeError, ValueError): return json_error("marks must be a number.")
    if marks <= 0: return json_error("marks must be greater than 0.")
    correct_count = sum(1 for x in options if isinstance(x, dict) and x.get("is_correct") is True)
    if correct_count != 1:
        return json_error("Exactly one option must have is_correct=true.")
    cur = db().execute("INSERT INTO questions(quiz_id,question_text,marks) VALUES(?,?,?)",
                        (quiz_id, text, marks))
    qid = cur.lastrowid
    for item in options:
        if not isinstance(item, dict) or not str(item.get("option_text","")).strip():
            db().rollback()
            return json_error("Each option needs option_text.")
        db().execute("INSERT INTO options(question_id,option_text,is_correct) VALUES(?,?,?)",
                     (qid, str(item["option_text"]).strip(), 1 if item.get("is_correct") is True else 0))
    db().commit()
    return jsonify({"success": True, "question_id": qid}), 201

@app.put("/api/questions/<int:question_id>")
@role_required("admin")
def update_question(question_id):
    question = db().execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
    if not question: return json_error("Question not found.", 404)
    data, err = validate_json(("question_text","options"))
    if err: return err
    text = str(data["question_text"]).strip()
    options = data["options"]
    if not text or not isinstance(options, list) or len(options) < 2:
        return json_error("Invalid question or options.")
    if sum(1 for x in options if isinstance(x, dict) and x.get("is_correct") is True) != 1:
        return json_error("Exactly one option must have is_correct=true.")
    conn = db()
    conn.execute("UPDATE questions SET question_text=?,marks=? WHERE id=?",
                 (text, float(data.get("marks", question["marks"])), question_id))
    conn.execute("DELETE FROM options WHERE question_id=?", (question_id,))
    for item in options:
        if not str(item.get("option_text","")).strip():
            conn.rollback()
            return json_error("Option text cannot be empty.")
        conn.execute("INSERT INTO options(question_id,option_text,is_correct) VALUES(?,?,?)",
                     (question_id, str(item["option_text"]).strip(), 1 if item.get("is_correct") is True else 0))
    conn.commit()
    return jsonify({"success": True, "message": "Question updated."})

@app.delete("/api/questions/<int:question_id>")
@role_required("admin")
def delete_question(question_id):
    cur = db().execute("DELETE FROM questions WHERE id=?", (question_id,))
    db().commit()
    if cur.rowcount == 0: return json_error("Question not found.", 404)
    return jsonify({"success": True, "message": "Question deleted."})

# -------------------- PARTICIPATION --------------------
@app.post("/api/quizzes/<int:quiz_id>/attempts")
@role_required("participant")
def start_attempt(quiz_id):
    quiz = db().execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,)).fetchone()
    if not quiz: return json_error("Quiz not found.", 404)
    count = db().execute("SELECT COUNT(*) FROM questions WHERE quiz_id=?", (quiz_id,)).fetchone()[0]
    if count == 0: return json_error("This quiz has no questions yet.", 409)
    cur = db().execute("""
        INSERT INTO attempts(quiz_id,user_id,started_at,total_marks)
        VALUES(?,?,?,?)
    """, (quiz_id, g.current_user["id"], utcnow(),
          db().execute("SELECT COALESCE(SUM(marks),0) FROM questions WHERE quiz_id=?", (quiz_id,)).fetchone()[0]))
    db().commit()
    return jsonify({"success": True, "attempt_id": cur.lastrowid, "started_at": utcnow()}), 201

@app.post("/api/attempts/<int:attempt_id>/submit")
@role_required("participant")
def submit_attempt(attempt_id):
    data, err = validate_json(("answers",))
    if err: return err
    attempt = db().execute("""
        SELECT a.*, q.negative_marking, q.title
        FROM attempts a JOIN quizzes q ON q.id=a.quiz_id
        WHERE a.id=? AND a.user_id=?
    """, (attempt_id, g.current_user["id"])).fetchone()
    if not attempt: return json_error("Attempt not found.", 404)
    if attempt["submitted_at"]: return json_error("This attempt has already been submitted.", 409)
    answers = data["answers"]
    if not isinstance(answers, list):
        return json_error("answers must be a list.")
    questions = db().execute("SELECT * FROM questions WHERE quiz_id=?", (attempt["quiz_id"],)).fetchall()
    qmap = {q["id"]: q for q in questions}
    if len(answers) > len(qmap):
        return json_error("Too many answers submitted.")
    submitted_qids = set()
    score = 0.0
    correct = wrong = 0
    for item in answers:
        if not isinstance(item, dict) or "question_id" not in item:
            return json_error("Each answer requires question_id.")
        try: qid = int(item["question_id"])
        except (TypeError, ValueError): return json_error("Invalid question_id.")
        if qid in submitted_qids:
            return json_error("Duplicate answer for question " + str(qid) + ".")
        submitted_qids.add(qid)
        if qid not in qmap:
            return json_error("Question does not belong to this quiz.")
        option_id = item.get("option_id")
        if option_id is None:
            db().execute("INSERT INTO answers(attempt_id,question_id,option_id,is_correct,marks_awarded) VALUES(?,?,?,?,?)",
                         (attempt_id,qid,None,0,0))
            continue
        try: option_id = int(option_id)
        except (TypeError, ValueError): return json_error("Invalid option_id.")
        option = db().execute("SELECT * FROM options WHERE id=? AND question_id=?", (option_id,qid)).fetchone()
        if not option:
            return json_error(f"Option {option_id} is invalid for question {qid}.")
        if option["is_correct"]:
            awarded = float(qmap[qid]["marks"])
            score += awarded
            correct += 1
            is_correct = 1
        else:
            awarded = -float(attempt["negative_marking"])
            score += awarded
            wrong += 1
            is_correct = 0
        db().execute("""INSERT INTO answers(attempt_id,question_id,option_id,is_correct,marks_awarded)
                        VALUES(?,?,?,?,?)""", (attempt_id,qid,option_id,is_correct,awarded))
    unanswered = len(qmap) - len(submitted_qids)
    for qid in qmap:
        if qid not in submitted_qids:
            db().execute("INSERT INTO answers(attempt_id,question_id,option_id,is_correct,marks_awarded) VALUES(?,?,?,?,?)",
                         (attempt_id,qid,None,0,0))
    total = float(attempt["total_marks"])
    # Percentage is capped at 0 for presentation; raw score is retained.
    percentage = max(0.0, (score / total * 100)) if total else 0.0
    passed = 1 if percentage >= 40 else 0
    db().execute("""
        UPDATE attempts SET submitted_at=?,score=?,correct_count=?,wrong_count=?,
        unanswered_count=?,percentage=?,passed=? WHERE id=?
    """, (utcnow(), score, correct, wrong, unanswered, percentage, passed, attempt_id))
    db().commit()
    return jsonify({
        "success": True, "result": {
            "attempt_id": attempt_id, "quiz": attempt["title"], "score": round(score,2),
            "total_marks": total, "correct": correct, "wrong": wrong,
            "unanswered": unanswered, "percentage": round(percentage,2),
            "passed": bool(passed)
        }
    })

@app.get("/api/my-results")
@role_required("participant")
def my_results():
    rows = db().execute("""
        SELECT a.*, q.title, q.difficulty
        FROM attempts a JOIN quizzes q ON q.id=a.quiz_id
        WHERE a.user_id=? AND a.submitted_at IS NOT NULL
        ORDER BY a.submitted_at DESC
    """, (g.current_user["id"],)).fetchall()
    return jsonify({"success": True, "results": [dict(r) for r in rows]})

# -------------------- LEADERBOARD / STATS --------------------
@app.get("/api/quizzes/<int:quiz_id>/leaderboard")
@auth_required
def leaderboard(quiz_id):
    if not db().execute("SELECT id FROM quizzes WHERE id=?", (quiz_id,)).fetchone():
        return json_error("Quiz not found.", 404)
    rows = db().execute("""
        SELECT u.username, MAX(a.score) AS best_score, MAX(a.percentage) AS best_percentage,
               COUNT(a.id) AS attempts
        FROM attempts a JOIN users u ON u.id=a.user_id
        WHERE a.quiz_id=? AND a.submitted_at IS NOT NULL
        GROUP BY u.id ORDER BY best_score DESC, best_percentage DESC, u.username ASC
    """, (quiz_id,)).fetchall()
    return jsonify({"success": True, "leaderboard": [dict(r) for r in rows]})

@app.get("/api/performance/<int:user_id>")
@auth_required
def performance(user_id):
    if g.current_user["role"] != "admin" and g.current_user["id"] != user_id:
        return json_error("You can only view your own performance.", 403)
    user = db().execute("SELECT id,username,email,role FROM users WHERE id=?", (user_id,)).fetchone()
    if not user: return json_error("User not found.", 404)
    stats = db().execute("""
        SELECT COUNT(*) attempts, COALESCE(AVG(percentage),0) average_percentage,
               COALESCE(MAX(percentage),0) best_percentage,
               COALESCE(SUM(correct_count),0) correct_answers,
               COALESCE(SUM(wrong_count),0) wrong_answers,
               COALESCE(SUM(unanswered_count),0) unanswered
        FROM attempts WHERE user_id=? AND submitted_at IS NOT NULL
    """, (user_id,)).fetchone()
    return jsonify({"success": True, "user": dict(user), "statistics": dict(stats)})

@app.get("/api/admin/statistics")
@role_required("admin")
def admin_statistics():
    quizzes = db().execute("SELECT COUNT(*) FROM quizzes").fetchone()[0]
    users = db().execute("SELECT COUNT(*) FROM users WHERE role='participant'").fetchone()[0]
    attempts = db().execute("SELECT COUNT(*) FROM attempts WHERE submitted_at IS NOT NULL").fetchone()[0]
    avg = db().execute("SELECT COALESCE(AVG(percentage),0) FROM attempts WHERE submitted_at IS NOT NULL").fetchone()[0]
    return jsonify({"success": True, "statistics": {
        "quizzes": quizzes, "participants": users, "completed_attempts": attempts,
        "average_percentage": round(avg,2)
    }})

# -------------------- API DOCUMENTATION --------------------
API_DOCS = {
    "authentication": {
        "POST /api/register": "Register participant. JSON: username,email,password",
        "POST /api/login": "Login. JSON: username,password. Returns Bearer token.",
        "POST /api/logout": "Authenticated user logout."
    },
    "quiz_admin": {
        "GET /api/quizzes": "List quizzes.",
        "GET /api/quizzes/<quiz_id>": "Get a quiz and its questions/options (correct answers hidden).",
        "POST /api/quizzes": "Admin: create quiz.",
        "PUT /api/quizzes/<quiz_id>": "Admin: update quiz.",
        "DELETE /api/quizzes/<quiz_id>": "Admin: delete quiz.",
        "POST /api/quizzes/<quiz_id>/questions": "Admin: add question with options.",
        "PUT /api/questions/<question_id>": "Admin: update question.",
        "DELETE /api/questions/<question_id>": "Admin: delete question."
    },
    "participant": {
        "POST /api/quizzes/<quiz_id>/attempts": "Participant: start attempt.",
        "POST /api/attempts/<attempt_id>/submit": "Participant: submit answers; server validates and calculates score.",
        "GET /api/my-results": "Participant: result history.",
        "GET /api/performance/<user_id>": "Own performance, or any user as admin."
    },
    "analytics": {
        "GET /api/quizzes/<quiz_id>/leaderboard": "Leaderboard using each user's best score.",
        "GET /api/admin/statistics": "Admin platform statistics."
    }
}

@app.get("/api/docs")
def api_docs():
    return jsonify({"success": True, "base_url": request.host_url.rstrip("/"), "endpoints": API_DOCS})

# -------------------- SIMPLE REAL WEB APP --------------------
HTML = r"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>QuizMaster — Online Quiz System</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,Arial,sans-serif;background:#0b1020;color:#eef2ff}
nav{height:64px;padding:0 5%;display:flex;align-items:center;justify-content:space-between;background:#121a31;border-bottom:1px solid #273253}
.brand{font-size:22px;font-weight:800;color:#7dd3fc}.wrap{max-width:1100px;margin:30px auto;padding:0 18px}
.card{background:#121a31;border:1px solid #273253;border-radius:18px;padding:22px;margin:16px 0;box-shadow:0 10px 35px #0003}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
input,textarea,select{width:100%;padding:12px;border-radius:10px;border:1px solid #354264;background:#0d1428;color:white;margin:6px 0 12px}
button{border:0;border-radius:10px;padding:11px 16px;background:#2563eb;color:#fff;font-weight:700;cursor:pointer;margin:4px}
button.secondary{background:#334155}button.danger{background:#dc2626}
h1,h2,h3{margin-top:0}.muted{color:#9aa8c7}.pill{display:inline-block;padding:5px 9px;border-radius:999px;background:#1e3a5f;color:#93c5fd;font-size:12px;margin:3px}
.hidden{display:none}.question{padding:18px;border:1px solid #2a385c;border-radius:14px;margin:12px 0}
.option{display:block;padding:10px;border-radius:9px;margin:7px 0;background:#0c1428}.option:hover{background:#17233f}
.alert{padding:12px;border-radius:10px;background:#172554;margin:12px 0}.error{background:#4c1d1d}.success{background:#14532d}
table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #293554;text-align:left}
header.hero{padding:28px 0}.stat{font-size:28px;font-weight:800}
</style>
</head>
<body>
<nav><div class="brand">🎯 QuizMaster</div><div id="nav"></div></nav>
<div class="wrap">
<div id="app"></div>
</div>
<script>
let token=localStorage.getItem("quiz_token")||"", me=null;
const $=id=>document.getElementById(id);
async function api(url,opt={}){opt.headers=opt.headers||{};opt.headers["Content-Type"]="application/json";if(token)opt.headers.Authorization="Bearer "+token;
let r=await fetch(url,opt),d=await r.json().catch(()=>({error:"Invalid server response"}));if(!r.ok)throw Error(d.error||"Request failed");return d}
function msg(text,ok=false){return `<div class="alert ${ok?'success':'error'}">${text}</div>`}
function nav(){ $("nav").innerHTML=me?`<span>${me.username} (${me.role})</span><button class="secondary" onclick="logout()">Logout</button>`:`<button onclick="loginPage()">Login</button><button onclick="registerPage()">Register</button>`}
async function boot(){if(token){try{me=(await api("/api/me")).user}catch(e){token="";localStorage.removeItem("quiz_token")}}nav();home()}
function loginPage(){ $("app").innerHTML=`<div class="card"><h2>Login</h2><input id="u" placeholder="Username or email"><input id="p" type="password" placeholder="Password"><button onclick="login()">Login</button><button class="secondary" onclick="home()">Back</button><p class="muted">Demo admin: admin / admin123<br>Demo participant: student / student123</p><div id="m"></div></div>`}
async function login(){try{let d=await api("/api/login",{method:"POST",body:JSON.stringify({username:$("u").value,password:$("p").value})});token=d.token;localStorage.setItem("quiz_token",token);me=d.user;nav();home()}catch(e){$("m").innerHTML=msg(e.message)}}
function registerPage(){ $("app").innerHTML=`<div class="card"><h2>Create Participant Account</h2><input id="ru" placeholder="Username"><input id="re" placeholder="Email"><input id="rp" type="password" placeholder="Password (6+ chars)"><button onclick="register()">Register</button><button class="secondary" onclick="home()">Back</button><div id="m"></div></div>`}
async function register(){try{await api("/api/register",{method:"POST",body:JSON.stringify({username:$("ru").value,email:$("re").value,password:$("rp").value})});$("m").innerHTML=msg("Registration successful. You can now login.",true)}catch(e){$("m").innerHTML=msg(e.message)}}
async function logout(){try{await api("/api/logout",{method:"POST"})}catch(e){}token="";me=null;localStorage.removeItem("quiz_token");nav();home()}
async function home(){let d=await api("/api/quizzes");let html=`<header class="hero"><h1>Online Quiz System</h1><p class="muted">Secure quizzes, automatic scoring, result history and leaderboard.</p></header>`;
if(!me)html+=`<div class="card">${msg("Login as a participant to take quizzes, or as admin to manage them.",true)}</div>`;
if(me?.role==="admin")html+=`<div class="card"><h2>Admin Dashboard</h2><button onclick="createQuizPage()">+ Create Quiz</button><button class="secondary" onclick="adminStats()">Statistics</button></div>`;
html+=`<h2>Available Quizzes</h2><div class="grid">`;
for(let q of d.quizzes)html+=`<div class="card"><h3>${esc(q.title)}</h3><span class="pill">${q.difficulty}</span><span class="pill">${q.time_limit?q.time_limit+" min":"No time limit"}</span><p class="muted">${esc(q.description||"No description")}</p><button onclick="viewQuiz(${q.id})">Open</button>${me?.role==="admin"?`<button class="danger" onclick="delQuiz(${q.id})">Delete</button>`:""}</div>`;
html+=`</div><div id="extra"></div>`;$("app").innerHTML=html}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
async function viewQuiz(id){let d;try{d=await api("/api/quizzes/"+id)}catch(e){$("app").innerHTML=msg(e.message);return}
let q=d.quiz,html=`<div class="card"><button class="secondary" onclick="home()">← Back</button><h2>${esc(q.title)}</h2><p>${esc(q.description||"")}</p><span class="pill">${q.difficulty}</span><span class="pill">Negative: ${q.negative_marking}</span>`;
if(me?.role==="admin"){html+=`<button onclick="addQuestionPage(${id})">+ Add Question</button>`}
if(me?.role==="participant"){html+=`<button onclick="startQuiz(${id})">Start Quiz</button>`}
html+=`</div><div class="card"><h3>${d.questions.length} Questions</h3>`;
d.questions.forEach((x,i)=>{html+=`<div class="question"><b>${i+1}. ${esc(x.question_text)}</b>${x.options.map(o=>`<div class="option">${esc(o.option_text)}</div>`).join("")}</div>`});html+=`</div>`;
$("app").innerHTML=html}
async function startQuiz(id){try{let a=await api(`/api/quizzes/${id}/attempts`,{method:"POST"});let q=await api(`/api/quizzes/${id}`);let html=`<div class="card"><button class="secondary" onclick="home()">Exit</button><h2>${esc(q.quiz.title)}</h2><p class="muted">Answer all questions and submit once.</p><form id="quizform">`;
q.questions.forEach((x,i)=>{html+=`<div class="question"><b>${i+1}. ${esc(x.question_text)}</b>${x.options.map(o=>`<label class="option"><input type="radio" name="q${x.id}" value="${o.id}"> ${esc(o.option_text)}</label>`).join("")}</div>`});
html+=`</form><button onclick="submitQuiz(${a.attempt_id},${id})">Submit Quiz</button><div id="result"></div></div>`;$("app").innerHTML=html}catch(e){$("app").innerHTML=msg(e.message)}}
async function submitQuiz(attempt,id){let els=document.querySelectorAll("input[type=radio]:checked"),answers=[];els.forEach(x=>answers.push({question_id:Number(x.name.substring(1)),option_id:Number(x.value)}));try{let d=await api(`/api/attempts/${attempt}/submit`,{method:"POST",body:JSON.stringify({answers})});$("result").innerHTML=msg(`Score: <b>${d.result.score}/${d.result.total_marks}</b> — ${d.result.percentage}% — ${d.result.passed?"PASSED":"NOT PASSED"}`,true)+`<button onclick="myResults()">View History</button><button onclick="leaderboard(${id})">Leaderboard</button>`}catch(e){$("result").innerHTML=msg(e.message)}}
async function myResults(){try{let d=await api("/api/my-results");let h=`<div class="card"><button class="secondary" onclick="home()">← Home</button><h2>My Result History</h2><table><tr><th>Quiz</th><th>Score</th><th>%</th><th>Status</th></tr>`;d.results.forEach(x=>h+=`<tr><td>${esc(x.title)}</td><td>${x.score}/${x.total_marks}</td><td>${x.percentage}%</td><td>${x.passed?"Passed":"Not passed"}</td></tr>`);h+="</table></div>";$("app").innerHTML=h}catch(e){$("app").innerHTML=msg(e.message)}}
async function leaderboard(id){try{let d=await api(`/api/quizzes/${id}/leaderboard`);let h=`<div class="card"><button class="secondary" onclick="home()">← Home</button><h2>Leaderboard</h2><table><tr><th>#</th><th>User</th><th>Best Score</th><th>%</th><th>Attempts</th></tr>`;d.leaderboard.forEach((x,i)=>h+=`<tr><td>${i+1}</td><td>${esc(x.username)}</td><td>${x.best_score}</td><td>${x.best_percentage}%</td><td>${x.attempts}</td></tr>`);h+="</table></div>";$("app").innerHTML=h}catch(e){$("app").innerHTML=msg(e.message)}}
function createQuizPage(){$("app").innerHTML=`<div class="card"><h2>Create Quiz</h2><input id="qt" placeholder="Title"><textarea id="qd" placeholder="Description"></textarea><select id="qdiff"><option>easy</option><option selected>medium</option><option>hard</option></select><input id="neg" type="number" step="0.1" value="0" placeholder="Negative marks per wrong answer"><input id="time" type="number" value="0" placeholder="Time in minutes (0 = none)"><button onclick="createQuiz()">Create</button><button class="secondary" onclick="home()">Cancel</button><div id="m"></div></div>`}
async function createQuiz(){try{let d=await api("/api/quizzes",{method:"POST",body:JSON.stringify({title:$("qt").value,description:$("qd").value,difficulty:$("qdiff").value,negative_marking:Number($("neg").value),time_limit:Number($("time").value)})});$("m").innerHTML=msg("Quiz created. Now add questions.",true);setTimeout(()=>viewQuiz(d.quiz_id),500)}catch(e){$("m").innerHTML=msg(e.message)}}
function addQuestionPage(id){$("app").innerHTML=`<div class="card"><h2>Add Question</h2><input id="qtext" placeholder="Question text"><input id="marks" type="number" value="1" step="0.5"><p class="muted">Enter four options. Mark the correct option.</p>${[1,2,3,4].map(i=>`<div><input id="o${i}" placeholder="Option ${i}"> <label><input type="radio" name="correct" value="${i}" ${i===1?"checked":""}> Correct</label></div>`).join("")}<button onclick="addQuestion(${id})">Save Question</button><button class="secondary" onclick="viewQuiz(${id})">Cancel</button><div id="m"></div></div>`}
async function addQuestion(id){let c=Number(document.querySelector('input[name=correct]:checked').value);let opts=[1,2,3,4].map(i=>({option_text:$("o"+i).value,is_correct:i===c}));try{await api(`/api/quizzes/${id}/questions`,{method:"POST",body:JSON.stringify({question_text:$("qtext").value,marks:Number($("marks").value),options:opts})});viewQuiz(id)}catch(e){$("m").innerHTML=msg(e.message)}}
async function delQuiz(id){if(!confirm("Delete this quiz and its questions/results?"))return;try{await api(`/api/quizzes/${id}`,{method:"DELETE"});home()}catch(e){alert(e.message)}}
async function adminStats(){try{let d=await api("/api/admin/statistics");$("extra").innerHTML=`<div class="card grid"><div><div class="stat">${d.statistics.quizzes}</div>Quizzes</div><div><div class="stat">${d.statistics.participants}</div>Participants</div><div><div class="stat">${d.statistics.completed_attempts}</div>Completed attempts</div><div><div class="stat">${d.statistics.average_percentage}%</div>Average score</div></div>`}catch(e){alert(e.message)}}
boot();
</script>
</body>
</html>
"""

@app.get("/")
def index():
    return render_template_string(HTML)

@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "Online Quiz System"})

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
