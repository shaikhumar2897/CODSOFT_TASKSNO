const express = require("express");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = 5000;

const DATA_DIR = path.join(__dirname, "data");
const DB_FILE = path.join(DATA_DIR, "database.json");

app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

function createDatabase() {
    if (!fs.existsSync(DATA_DIR)) {
        fs.mkdirSync(DATA_DIR, { recursive: true });
    }

    if (!fs.existsSync(DB_FILE)) {
        fs.writeFileSync(DB_FILE, JSON.stringify({ contacts: [] }, null, 2));
    }
}

function readDatabase() {
    createDatabase();

    try {
        return JSON.parse(fs.readFileSync(DB_FILE, "utf8"));
    } catch (error) {
        return { contacts: [] };
    }
}

function saveDatabase(database) {
    fs.writeFileSync(DB_FILE, JSON.stringify(database, null, 2));
}

function nextId(items) {
    if (items.length === 0) return 1;
    return Math.max(...items.map(item => Number(item.id) || 0)) + 1;
}

function sendSuccess(res, message, data = null, status = 200) {
    return res.status(status).json({
        success: true,
        message,
        data
    });
}

function sendError(res, message, status = 400) {
    return res.status(status).json({
        success: false,
        message
    });
}

function validEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validPhone(phone) {
    return /^[0-9+\-\s()]{7,20}$/.test(phone);
}

function clean(value) {
    return String(value ?? "").trim();
}

createDatabase();

/* =====================================================
   HOME
===================================================== */

app.get("/", (req, res) => {
    res.sendFile(path.join(__dirname, "public", "index.html"));
});

/* =====================================================
   CONTACT APIs
===================================================== */

// GET all contacts
// Supports search, sorting and pagination.
//
// Examples:
// /api/contacts
// /api/contacts?search=umar
// /api/contacts?sort=name&order=asc
// /api/contacts?page=1&limit=5

app.get("/api/contacts", (req, res) => {
    const database = readDatabase();

    let contacts = [...database.contacts];

    const search = clean(req.query.search).toLowerCase();

    if (search) {
        contacts = contacts.filter(contact =>
            contact.name.toLowerCase().includes(search) ||
            contact.email.toLowerCase().includes(search) ||
            contact.phone.toLowerCase().includes(search) ||
            contact.address.toLowerCase().includes(search) ||
            contact.company.toLowerCase().includes(search)
        );
    }

    const sortField = ["name", "email", "company", "createdAt"].includes(req.query.sort)
        ? req.query.sort
        : "name";

    const order = req.query.order === "desc" ? -1 : 1;

    contacts.sort((a, b) => {
        const first = String(a[sortField] ?? "").toLowerCase();
        const second = String(b[sortField] ?? "").toLowerCase();

        if (first < second) return -1 * order;
        if (first > second) return 1 * order;
        return 0;
    });

    let page = Math.max(1, parseInt(req.query.page) || 1);
    let limit = Math.max(1, Math.min(100, parseInt(req.query.limit) || 10));

    const totalItems = contacts.length;
    const totalPages = Math.ceil(totalItems / limit);
    const start = (page - 1) * limit;

    return sendSuccess(res, "Contacts retrieved successfully", {
        contacts: contacts.slice(start, start + limit),
        pagination: {
            page,
            limit,
            totalItems,
            totalPages
        }
    });
});

// GET one contact
app.get("/api/contacts/:id", (req, res) => {
    const database = readDatabase();

    const contact = database.contacts.find(
        item => item.id === Number(req.params.id)
    );

    if (!contact) {
        return sendError(res, "Contact not found", 404);
    }

    return sendSuccess(res, "Contact retrieved successfully", contact);
});

// CREATE contact
app.post("/api/contacts", (req, res) => {
    const database = readDatabase();

    const name = clean(req.body.name);
    const email = clean(req.body.email);
    const phone = clean(req.body.phone);
    const address = clean(req.body.address);
    const company = clean(req.body.company);

    if (!name || !email || !phone || !address || !company) {
        return sendError(
            res,
            "Name, email, phone, address and company are required"
        );
    }

    if (!validEmail(email)) {
        return sendError(res, "Please enter a valid email address");
    }

    if (!validPhone(phone)) {
        return sendError(res, "Please enter a valid phone number");
    }

    const duplicateEmail = database.contacts.some(
        contact => contact.email.toLowerCase() === email.toLowerCase()
    );

    if (duplicateEmail) {
        return sendError(res, "A contact with this email already exists");
    }

    const duplicatePhone = database.contacts.some(
        contact => contact.phone === phone
    );

    if (duplicatePhone) {
        return sendError(res, "A contact with this phone number already exists");
    }

    const contact = {
        id: nextId(database.contacts),
        name,
        email,
        phone,
        address,
        company,
        createdAt: new Date().toISOString()
    };

    database.contacts.push(contact);
    saveDatabase(database);

    return sendSuccess(
        res,
        "Contact created successfully",
        contact,
        201
    );
});

// UPDATE contact
app.put("/api/contacts/:id", (req, res) => {
    const database = readDatabase();

    const contact = database.contacts.find(
        item => item.id === Number(req.params.id)
    );

    if (!contact) {
        return sendError(res, "Contact not found", 404);
    }

    const name = req.body.name !== undefined ? clean(req.body.name) : contact.name;
    const email = req.body.email !== undefined ? clean(req.body.email) : contact.email;
    const phone = req.body.phone !== undefined ? clean(req.body.phone) : contact.phone;
    const address = req.body.address !== undefined ? clean(req.body.address) : contact.address;
    const company = req.body.company !== undefined ? clean(req.body.company) : contact.company;

    if (!name || !email || !phone || !address || !company) {
        return sendError(res, "All contact fields are required");
    }

    if (!validEmail(email)) {
        return sendError(res, "Please enter a valid email address");
    }

    if (!validPhone(phone)) {
        return sendError(res, "Please enter a valid phone number");
    }

    const duplicateEmail = database.contacts.some(
        item =>
            item.id !== contact.id &&
            item.email.toLowerCase() === email.toLowerCase()
    );

    if (duplicateEmail) {
        return sendError(res, "Another contact already uses this email");
    }

    const duplicatePhone = database.contacts.some(
        item =>
            item.id !== contact.id &&
            item.phone === phone
    );

    if (duplicatePhone) {
        return sendError(res, "Another contact already uses this phone number");
    }

    contact.name = name;
    contact.email = email;
    contact.phone = phone;
    contact.address = address;
    contact.company = company;

    saveDatabase(database);

    return sendSuccess(
        res,
        "Contact updated successfully",
        contact
    );
});

// DELETE contact
app.delete("/api/contacts/:id", (req, res) => {
    const database = readDatabase();

    const index = database.contacts.findIndex(
        item => item.id === Number(req.params.id)
    );

    if (index === -1) {
        return sendError(res, "Contact not found", 404);
    }

    const deleted = database.contacts.splice(index, 1)[0];

    saveDatabase(database);

    return sendSuccess(
        res,
        "Contact deleted successfully",
        deleted
    );
});

// GET statistics
app.get("/api/stats", (req, res) => {
    const database = readDatabase();

    const companies = new Set(
        database.contacts.map(contact => contact.company.toLowerCase())
    );

    return sendSuccess(res, "Statistics retrieved successfully", {
        totalContacts: database.contacts.length,
        totalCompanies: companies.size,
        recentContacts: database.contacts.slice(-5).reverse()
    });
});

// Unknown API route
app.use("/api", (req, res) => {
    return sendError(res, "API route not found", 404);
});

// General 404
app.use((req, res) => {
    res.status(404).send("Page not found");
});

// Error handler
app.use((err, req, res, next) => {
    console.error(err);
    return sendError(res, "Internal server error", 500);
});

app.listen(PORT, () => {
    console.log("========================================");
    console.log(" CONTACT MANAGEMENT SYSTEM");
    console.log(" CodSoft Backend Development - Task 2");
    console.log("========================================");
    console.log(`Server running at http://localhost:${PORT}`);
    console.log(`API: http://localhost:${PORT}/api/contacts`);
    console.log("========================================");
});
