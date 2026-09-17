# Task 5 — Online Quiz System

A complete Flask + SQLite backend and browser UI for the CodSoft Backend Development Internship Task 5.

## Features
- Admin and participant authentication using Bearer tokens.
- Passwords are securely hashed.
- SQLite database with users, quizzes, questions, options, attempts, answers and API tokens.
- Admin can create/update/delete quizzes and add/update/delete questions.
- Participants can start quizzes and submit answers.
- Server validates question IDs and option IDs before scoring.
- Automatic scoring with optional negative marking.
- Result history for every participant.
- Quiz leaderboard and performance statistics.
- Admin statistics dashboard.
- Responsive browser UI at `/`.
- API documentation at `/api/docs`.
- Health check at `/health`.

## Demo accounts
- Admin: `admin` / `admin123`
- Participant: `student` / `student123`

Change these before using the project publicly.

## Run in VS Code / terminal

```bash
python -m venv venv
```

Windows:
```bash
venv\Scripts\activate
```

macOS/Linux:
```bash
source venv/bin/activate
```

Install:
```bash
pip install -r requirements.txt
```

Run:
```bash
python app.py
```

Open:
`http://127.0.0.1:5000`

The SQLite database `quiz.db` is created automatically.

## REST API examples

Login:
```http
POST /api/login
Content-Type: application/json

{"username":"admin","password":"admin123"}
```

Use the returned token:
```http
Authorization: Bearer YOUR_TOKEN
```

Create quiz (admin):
```http
POST /api/quizzes
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "title":"Python Basics",
  "description":"Beginner Python quiz",
  "difficulty":"easy",
  "negative_marking":0.25,
  "time_limit":10
}
```

Add question:
```http
POST /api/quizzes/1/questions
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "question_text":"Which keyword defines a function in Python?",
  "marks":1,
  "options":[
    {"option_text":"func","is_correct":false},
    {"option_text":"def","is_correct":true},
    {"option_text":"function","is_correct":false},
    {"option_text":"define","is_correct":false}
  ]
}
```

Participant starts an attempt:
```http
POST /api/quizzes/1/attempts
Authorization: Bearer PARTICIPANT_TOKEN
```

Submit:
```http
POST /api/attempts/1/submit
Authorization: Bearer PARTICIPANT_TOKEN
Content-Type: application/json

{
  "answers":[
    {"question_id":1,"option_id":2}
  ]
}
```

## API documentation
After starting the server, visit:
`http://127.0.0.1:5000/api/docs`

## Testing
Run:
```bash
python -m unittest -v
```

The test suite checks health, registration, login, role protection, quiz creation, question creation, quiz listing, participant attempts, answer validation, scoring, result history, leaderboard and performance.
