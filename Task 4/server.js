const express = require("express");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = 5000;

app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

const DATA_DIR = path.join(__dirname, "data");
const DB_FILE = path.join(DATA_DIR, "database.json");

function createDatabase() {
    if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
    if (!fs.existsSync(DB_FILE)) {
        fs.writeFileSync(DB_FILE, JSON.stringify({
            authors: [], books: [], members: [], issuedBooks: []
        }, null, 2));
    }
}

function readDatabase() {
    createDatabase();
    try {
        return JSON.parse(fs.readFileSync(DB_FILE, "utf8"));
    } catch {
        return { authors: [], books: [], members: [], issuedBooks: [] };
    }
}

function saveDatabase(db) {
    fs.writeFileSync(DB_FILE, JSON.stringify(db, null, 2));
}

function nextId(arr) {
    return arr.length ? Math.max(...arr.map(x => Number(x.id) || 0)) + 1 : 1;
}

function ok(res, message, data = null, status = 200) {
    res.status(status).json({ success: true, message, data });
}

function fail(res, message, status = 400) {
    res.status(status).json({ success: false, message });
}

function pagination(req, items) {
    let page = Math.max(1, parseInt(req.query.page) || 1);
    let limit = Math.max(1, Math.min(100, parseInt(req.query.limit) || 10));
    const totalItems = items.length;
    const totalPages = Math.ceil(totalItems / limit);
    const start = (page - 1) * limit;
    return {
        data: items.slice(start, start + limit),
        pagination: { page, limit, totalItems, totalPages }
    };
}

function overdue(issue) {
    const due = new Date(issue.dueDate);
    const end = issue.returnDate ? new Date(issue.returnDate) : new Date();
    const days = Math.max(0, Math.ceil((end - due) / 86400000));
    return { overdueDays: days, lateFee: days * 5 };
}

app.get("/", (req, res) => ok(res, "Library Management System API is running", {
    task: "CodSoft Backend Development - Task 4",
    port: PORT,
    endpoints: [
        "GET/POST/PUT/DELETE /api/authors",
        "GET/POST/PUT/DELETE /api/books",
        "GET/POST/PUT/DELETE /api/members",
        "GET /api/issues",
        "POST /api/issues",
        "PUT /api/issues/:id/return",
        "GET /api/reports"
    ]
}));

// ---------------- AUTHORS ----------------
app.get("/api/authors", (req, res) => {
    const db = readDatabase();
    let items = db.authors;
    if (req.query.search) {
        const s = req.query.search.toLowerCase();
        items = items.filter(a => a.name.toLowerCase().includes(s) || a.email.toLowerCase().includes(s));
    }
    ok(res, "Authors retrieved successfully", pagination(req, items));
});

app.get("/api/authors/:id", (req, res) => {
    const db = readDatabase();
    const item = db.authors.find(a => a.id === Number(req.params.id));
    if (!item) return fail(res, "Author not found", 404);
    ok(res, "Author retrieved successfully", item);
});

app.post("/api/authors", (req, res) => {
    const db = readDatabase();
    const { name, email } = req.body;
    if (!name || !email) return fail(res, "Name and email are required");
    if (db.authors.some(a => a.email.toLowerCase() === String(email).toLowerCase()))
        return fail(res, "Author email already exists");
    const author = { id: nextId(db.authors), name: String(name).trim(), email: String(email).trim() };
    db.authors.push(author);
    saveDatabase(db);
    ok(res, "Author created successfully", author, 201);
});

app.put("/api/authors/:id", (req, res) => {
    const db = readDatabase();
    const author = db.authors.find(a => a.id === Number(req.params.id));
    if (!author) return fail(res, "Author not found", 404);
    if (req.body.name !== undefined && !String(req.body.name).trim()) return fail(res, "Name cannot be empty");
    if (req.body.email !== undefined && !String(req.body.email).trim()) return fail(res, "Email cannot be empty");
    if (req.body.name !== undefined) author.name = String(req.body.name).trim();
    if (req.body.email !== undefined) author.email = String(req.body.email).trim();
    saveDatabase(db);
    ok(res, "Author updated successfully", author);
});

app.delete("/api/authors/:id", (req, res) => {
    const db = readDatabase();
    const id = Number(req.params.id);
    if (db.books.some(b => b.authorId === id))
        return fail(res, "Cannot delete author because books are associated with this author");
    const index = db.authors.findIndex(a => a.id === id);
    if (index === -1) return fail(res, "Author not found", 404);
    const deleted = db.authors.splice(index, 1)[0];
    saveDatabase(db);
    ok(res, "Author deleted successfully", deleted);
});

// ---------------- BOOKS ----------------
app.get("/api/books", (req, res) => {
    const db = readDatabase();
    let items = db.books.map(book => ({
        ...book,
        author: db.authors.find(a => a.id === book.authorId) || null
    }));
    if (req.query.search) {
        const s = req.query.search.toLowerCase();
        items = items.filter(b => b.title.toLowerCase().includes(s) || b.isbn.toLowerCase().includes(s));
    }
    if (req.query.category)
        items = items.filter(b => b.category.toLowerCase() === String(req.query.category).toLowerCase());
    if (req.query.authorId)
        items = items.filter(b => b.authorId === Number(req.query.authorId));
    if (req.query.available === "true")
        items = items.filter(b => b.availableCopies > 0);
    ok(res, "Books retrieved successfully", pagination(req, items));
});

app.get("/api/books/:id", (req, res) => {
    const db = readDatabase();
    const book = db.books.find(b => b.id === Number(req.params.id));
    if (!book) return fail(res, "Book not found", 404);
    ok(res, "Book retrieved successfully", {
        ...book,
        author: db.authors.find(a => a.id === book.authorId) || null
    });
});

app.post("/api/books", (req, res) => {
    const db = readDatabase();
    const { title, isbn, authorId, category, year, totalCopies } = req.body;
    if (!title || !isbn || !authorId || !category || year === undefined || totalCopies === undefined)
        return fail(res, "title, isbn, authorId, category, year and totalCopies are required");
    if (!db.authors.some(a => a.id === Number(authorId)))
        return fail(res, "Author does not exist");
    if (db.books.some(b => b.isbn === String(isbn).trim()))
        return fail(res, "ISBN already exists");
    if (Number(totalCopies) < 1) return fail(res, "Total copies must be at least 1");
    const book = {
        id: nextId(db.books),
        title: String(title).trim(),
        isbn: String(isbn).trim(),
        authorId: Number(authorId),
        category: String(category).trim(),
        year: Number(year),
        totalCopies: Number(totalCopies),
        availableCopies: Number(totalCopies)
    };
    db.books.push(book);
    saveDatabase(db);
    ok(res, "Book created successfully", book, 201);
});

app.put("/api/books/:id", (req, res) => {
    const db = readDatabase();
    const book = db.books.find(b => b.id === Number(req.params.id));
    if (!book) return fail(res, "Book not found", 404);

    if (req.body.authorId !== undefined && !db.authors.some(a => a.id === Number(req.body.authorId)))
        return fail(res, "Author does not exist");

    if (req.body.title !== undefined) book.title = String(req.body.title).trim();
    if (req.body.isbn !== undefined) book.isbn = String(req.body.isbn).trim();
    if (req.body.authorId !== undefined) book.authorId = Number(req.body.authorId);
    if (req.body.category !== undefined) book.category = String(req.body.category).trim();
    if (req.body.year !== undefined) book.year = Number(req.body.year);

    if (req.body.totalCopies !== undefined) {
        const newTotal = Number(req.body.totalCopies);
        const borrowed = book.totalCopies - book.availableCopies;
        if (newTotal < borrowed || newTotal < 1)
            return fail(res, "Total copies cannot be less than currently borrowed copies");
        book.totalCopies = newTotal;
        book.availableCopies = newTotal - borrowed;
    }

    saveDatabase(db);
    ok(res, "Book updated successfully", book);
});

app.delete("/api/books/:id", (req, res) => {
    const db = readDatabase();
    const id = Number(req.params.id);
    if (db.issuedBooks.some(i => i.bookId === id && i.status === "issued"))
        return fail(res, "Cannot delete a book that is currently issued");
    const index = db.books.findIndex(b => b.id === id);
    if (index === -1) return fail(res, "Book not found", 404);
    const deleted = db.books.splice(index, 1)[0];
    saveDatabase(db);
    ok(res, "Book deleted successfully", deleted);
});

// ---------------- MEMBERS ----------------
app.get("/api/members", (req, res) => {
    const db = readDatabase();
    let items = db.members;
    if (req.query.search) {
        const s = req.query.search.toLowerCase();
        items = items.filter(m =>
            m.name.toLowerCase().includes(s) ||
            m.email.toLowerCase().includes(s) ||
            m.phone.includes(s)
        );
    }
    ok(res, "Members retrieved successfully", pagination(req, items));
});

app.get("/api/members/:id", (req, res) => {
    const db = readDatabase();
    const member = db.members.find(m => m.id === Number(req.params.id));
    if (!member) return fail(res, "Member not found", 404);
    ok(res, "Member retrieved successfully", member);
});

app.post("/api/members", (req, res) => {
    const db = readDatabase();
    const { name, email, phone, membershipType } = req.body;
    if (!name || !email || !phone)
        return fail(res, "Name, email and phone are required");
    if (db.members.some(m => m.email.toLowerCase() === String(email).toLowerCase()))
        return fail(res, "Member email already exists");
    const member = {
        id: nextId(db.members),
        name: String(name).trim(),
        email: String(email).trim(),
        phone: String(phone).trim(),
        membershipType: String(membershipType || "Student").trim()
    };
    db.members.push(member);
    saveDatabase(db);
    ok(res, "Member created successfully", member, 201);
});

app.put("/api/members/:id", (req, res) => {
    const db = readDatabase();
    const member = db.members.find(m => m.id === Number(req.params.id));
    if (!member) return fail(res, "Member not found", 404);
    ["name", "email", "phone", "membershipType"].forEach(k => {
        if (req.body[k] !== undefined) member[k] = String(req.body[k]).trim();
    });
    saveDatabase(db);
    ok(res, "Member updated successfully", member);
});

app.delete("/api/members/:id", (req, res) => {
    const db = readDatabase();
    const id = Number(req.params.id);
    if (db.issuedBooks.some(i => i.memberId === id && i.status === "issued"))
        return fail(res, "Cannot delete a member with an active borrowed book");
    const index = db.members.findIndex(m => m.id === id);
    if (index === -1) return fail(res, "Member not found", 404);
    const deleted = db.members.splice(index, 1)[0];
    saveDatabase(db);
    ok(res, "Member deleted successfully", deleted);
});

// ---------------- ISSUE / RETURN ----------------
app.get("/api/issues", (req, res) => {
    const db = readDatabase();
    let items = db.issuedBooks.map(issue => ({
        ...issue,
        book: db.books.find(b => b.id === issue.bookId) || null,
        member: db.members.find(m => m.id === issue.memberId) || null,
        ...overdue(issue)
    }));

    if (req.query.status)
        items = items.filter(i => i.status === req.query.status);
    if (req.query.memberId)
        items = items.filter(i => i.memberId === Number(req.query.memberId));
    if (req.query.bookId)
        items = items.filter(i => i.bookId === Number(req.query.bookId));

    ok(res, "Borrowing records retrieved successfully", pagination(req, items));
});

app.post("/api/issues", (req, res) => {
    const db = readDatabase();
    const { bookId, memberId, days } = req.body;

    if (!bookId || !memberId)
        return fail(res, "bookId and memberId are required");

    const book = db.books.find(b => b.id === Number(bookId));
    if (!book) return fail(res, "Book not found", 404);

    const member = db.members.find(m => m.id === Number(memberId));
    if (!member) return fail(res, "Member not found", 404);

    if (book.availableCopies < 1)
        return fail(res, "Book is currently unavailable");

    const activeForMember = db.issuedBooks.filter(
        i => i.memberId === member.id && i.status === "issued"
    );

    if (activeForMember.length >= 3)
        return fail(res, "Borrowing limit reached. A member can have maximum 3 active books.");

    if (activeForMember.some(i => i.bookId === book.id))
        return fail(res, "This member already has this book");

    const issueDate = new Date();
    const borrowDays = Math.max(1, Math.min(30, Number(days) || 14));
    const dueDate = new Date(issueDate);
    dueDate.setDate(dueDate.getDate() + borrowDays);

    const issue = {
        id: nextId(db.issuedBooks),
        bookId: book.id,
        memberId: member.id,
        issueDate: issueDate.toISOString(),
        dueDate: dueDate.toISOString(),
        returnDate: null,
        status: "issued"
    };

    book.availableCopies -= 1;
    db.issuedBooks.push(issue);

    saveDatabase(db);

    ok(res, "Book issued successfully", {
        ...issue,
        book: book.title,
        member: member.name
    }, 201);
});

app.put("/api/issues/:id/return", (req, res) => {
    const db = readDatabase();
    const issue = db.issuedBooks.find(i => i.id === Number(req.params.id));

    if (!issue) return fail(res, "Borrowing record not found", 404);
    if (issue.status === "returned")
        return fail(res, "Book has already been returned");

    const book = db.books.find(b => b.id === issue.bookId);
    if (book) book.availableCopies = Math.min(book.totalCopies, book.availableCopies + 1);

    issue.returnDate = new Date().toISOString();
    issue.status = "returned";

    const fees = overdue(issue);

    saveDatabase(db);

    ok(res, "Book returned successfully", {
        issue,
        overdueDays: fees.overdueDays,
        lateFee: fees.lateFee
    });
});

// ---------------- REPORTS ----------------
app.get("/api/reports", (req, res) => {
    const db = readDatabase();

    const active = db.issuedBooks.filter(i => i.status === "issued");
    const returned = db.issuedBooks.filter(i => i.status === "returned");

    const overdueRecords = active
        .map(i => ({ ...i, ...overdue(i) }))
        .filter(i => i.overdueDays > 0);

    const totalCopies = db.books.reduce((sum, b) => sum + b.totalCopies, 0);
    const availableCopies = db.books.reduce((sum, b) => sum + b.availableCopies, 0);

    const lateFees = db.issuedBooks
        .map(i => overdue(i).lateFee)
        .reduce((sum, fee) => sum + fee, 0);

    ok(res, "Library report generated successfully", {
        totalBooks: db.books.length,
        totalAuthors: db.authors.length,
        totalMembers: db.members.length,
        totalCopies,
        availableCopies,
        borrowedCopies: totalCopies - availableCopies,
        activeIssues: active.length,
        returnedBooks: returned.length,
        overdueBooks: overdueRecords.length,
        estimatedLateFees: lateFees,
        overdueRecords
    });
});

// ---------------- 404 + ERROR ----------------
app.use((req, res) => {
    fail(res, "Route not found", 404);
});

app.use((err, req, res, next) => {
    console.error(err);
    fail(res, "Internal server error", 500);
});

app.listen(PORT, () => {
    console.log("======================================");
    console.log(" LIBRARY MANAGEMENT SYSTEM");
    console.log(" CodSoft Task 4");
    console.log("======================================");
    console.log(`Server running at http://localhost:${PORT}`);
    console.log(`API home: http://localhost:${PORT}/`);
    console.log("======================================");
});
