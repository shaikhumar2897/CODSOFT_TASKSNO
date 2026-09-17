# CodSoft Task 2 - Contact Management System

## Technology

- Node.js
- Express.js
- HTML
- CSS
- JavaScript
- Local JSON data storage

No MongoDB, MySQL or external database is required.

## Requirements implemented

- Express.js REST backend
- Contact fields:
  - Name
  - Email
  - Phone number
  - Address
  - Company / Organization
- Add contact
- Update contact
- Delete contact
- Retrieve contacts
- Search by name, email, phone, address or company
- Sorting
- Pagination support
- Input validation
- Duplicate email validation
- Duplicate phone validation
- Meaningful HTTP status codes
- Error responses
- Scalable folder structure
- Working browser user interface

## Run

Open PowerShell inside the project folder:

```powershell
npm install
npm start
```

Open:

http://localhost:5000

## REST API

GET /api/contacts

GET /api/contacts/:id

POST /api/contacts

PUT /api/contacts/:id

DELETE /api/contacts/:id

GET /api/stats

## Example POST

POST http://localhost:5000/api/contacts

```json
{
  "name": "Amit Kumar",
  "email": "amit@example.com",
  "phone": "9876543213",
  "address": "Mumbai, Maharashtra",
  "company": "ABC Technologies"
}
```

## Search

GET:

/api/contacts?search=amit

## Sorting

/api/contacts?sort=name&order=asc

/api/contacts?sort=company&order=desc

## Pagination

/api/contacts?page=1&limit=5
