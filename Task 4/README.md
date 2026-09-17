# CodSoft Task 4 - Library Management System

## Requirements covered

- Express.js backend
- Authors, books, members and issued books
- Add, update, delete and retrieve records
- Book availability tracking
- Borrowing and returning rules
- Search and filtering
- Pagination
- Input validation
- HTTP status codes
- Error handling
- Overdue days
- Late fee calculation
- Library reports
- No MongoDB/MySQL required

## Run

Open PowerShell in this folder:

```powershell
npm install
npm start
```

Then open:

http://localhost:5000

## Main APIs

### Authors
GET    /api/authors
GET    /api/authors/:id
POST   /api/authors
PUT    /api/authors/:id
DELETE /api/authors/:id

### Books
GET    /api/books
GET    /api/books/:id
POST   /api/books
PUT    /api/books/:id
DELETE /api/books/:id

Search:
GET /api/books?search=clean

Category:
GET /api/books?category=Programming

Available:
GET /api/books?available=true

Pagination:
GET /api/books?page=1&limit=2

### Members
GET    /api/members
GET    /api/members/:id
POST   /api/members
PUT    /api/members/:id
DELETE /api/members/:id

### Borrowing
GET  /api/issues
POST /api/issues
PUT  /api/issues/:id/return

### Reports
GET /api/reports

## Example: Add a book

POST /api/books

JSON:
{
  "title": "The Alchemist",
  "isbn": "9780061122415",
  "authorId": 3,
  "category": "Fiction",
  "year": 1988,
  "totalCopies": 5
}

## Example: Issue a book

POST /api/issues

JSON:
{
  "bookId": 1,
  "memberId": 1,
  "days": 14
}

## Example: Return a book

PUT /api/issues/1/return

No body is required.

## Late fee

The project uses a simple ₹5 per overdue day calculation for the bonus requirement.

## Testing

You can use a browser for GET APIs and Thunder Client/Postman for POST, PUT and DELETE APIs.


## Web User Interface

The project now includes a complete browser UI connected to the REST API.

Open:
http://localhost:5000

The UI supports:
- Dashboard
- Add/delete authors
- Add/delete members
- Add/edit/delete books
- Search and category filtering
- Availability filtering
- Issue books
- Return books
- Overdue and late-fee display
- Library reports

All actions update `data/database.json` through the backend APIs.
