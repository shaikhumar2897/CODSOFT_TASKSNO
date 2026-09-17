const API = "/api";

function $(id) {
    return document.getElementById(id);
}

async function request(url, options = {}) {
    const response = await fetch(API + url, {
        headers: { "Content-Type": "application/json" },
        ...options
    });

    const data = await response.json().catch(() => ({
        success: false,
        message: "Invalid server response"
    }));

    if (!response.ok || data.success === false) {
        throw new Error(data.message || "Request failed");
    }

    return data;
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    }[char]));
}

function showToast(message, error = false) {
    const toast = $("toast");
    toast.textContent = message;
    toast.style.background = error ? "#b91c1c" : "#111827";
    toast.style.display = "block";

    clearTimeout(window.toastTimer);
    window.toastTimer = setTimeout(() => {
        toast.style.display = "none";
    }, 2500);
}

function go(page) {
    document.querySelectorAll(".page").forEach(x => x.classList.remove("active"));
    $(page).classList.add("active");

    document.querySelectorAll(".nav").forEach(x => {
        x.classList.toggle("active", x.dataset.page === page);
    });

    const info = {
        dashboard: ["Dashboard", "Manage your personal and professional contacts"],
        contacts: ["Contacts", "Create, update, search and manage contacts"]
    };

    $("title").textContent = info[page][0];
    $("subtitle").textContent = info[page][1];

    if (page === "dashboard") loadDashboard();
    if (page === "contacts") loadContacts();

    document.querySelector(".sidebar").classList.remove("open");
}

document.querySelectorAll(".nav").forEach(button => {
    button.addEventListener("click", () => go(button.dataset.page));
});

$("menu").onclick = () => {
    document.querySelector(".sidebar").classList.toggle("open");
};

async function loadDashboard() {
    try {
        const result = await request("/stats");
        const data = result.data;

        $("totalContacts").textContent = data.totalContacts;
        $("totalCompanies").textContent = data.totalCompanies;

        $("recent").innerHTML = data.recentContacts.length
            ? makeTable(data.recentContacts, true)
            : '<div class="empty">No contacts available.</div>';
    } catch (error) {
        showToast(error.message, true);
    }
}

async function loadContacts() {
    try {
        const search = encodeURIComponent($("search").value);
        const sort = $("sort").value;
        const order = $("order").value;

        const result = await request(
            `/contacts?limit=100&search=${search}&sort=${sort}&order=${order}`
        );

        const contacts = result.data.contacts;

        $("count").textContent =
            `${result.data.pagination.totalItems} contact${result.data.pagination.totalItems === 1 ? "" : "s"}`;

        $("contactTable").innerHTML = contacts.length
            ? makeTable(contacts, false)
            : '<div class="empty">🔎 No contacts found.</div>';
    } catch (error) {
        showToast(error.message, true);
    }
}

function initials(name) {
    return String(name)
        .split(" ")
        .map(x => x[0])
        .slice(0, 2)
        .join("")
        .toUpperCase();
}

function makeTable(contacts, compact) {
    return `
        <table>
            <thead>
                <tr>
                    <th>Contact</th>
                    <th>Phone</th>
                    <th>Email</th>
                    <th>Company</th>
                    <th>Address</th>
                    ${compact ? "" : "<th>Actions</th>"}
                </tr>
            </thead>
            <tbody>
                ${contacts.map(contact => `
                    <tr>
                        <td>
                            <div class="person">
                                <span class="avatar">${escapeHTML(initials(contact.name))}</span>
                                <b>${escapeHTML(contact.name)}</b>
                            </div>
                        </td>
                        <td>${escapeHTML(contact.phone)}</td>
                        <td>${escapeHTML(contact.email)}</td>
                        <td>${escapeHTML(contact.company)}</td>
                        <td>${escapeHTML(contact.address)}</td>
                        ${compact ? "" : `
                            <td>
                                <button class="action" onclick="editContact(${contact.id})">Edit</button>
                                <button class="action delete" onclick="deleteContact(${contact.id})">Delete</button>
                            </td>
                        `}
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

function openAdd() {
    $("modalTitle").textContent = "Add Contact";
    $("saveBtn").textContent = "Save Contact";
    $("contactForm").reset();
    $("contactId").value = "";
    $("modal").classList.add("show");
}

function closeModal() {
    $("modal").classList.remove("show");
}

async function editContact(id) {
    try {
        const result = await request(`/contacts/${id}`);
        const contact = result.data;

        $("modalTitle").textContent = "Edit Contact";
        $("saveBtn").textContent = "Update Contact";

        $("contactId").value = contact.id;
        $("name").value = contact.name;
        $("email").value = contact.email;
        $("phone").value = contact.phone;
        $("address").value = contact.address;
        $("company").value = contact.company;

        $("modal").classList.add("show");
    } catch (error) {
        showToast(error.message, true);
    }
}

$("contactForm").addEventListener("submit", async event => {
    event.preventDefault();

    const id = $("contactId").value;

    const body = {
        name: $("name").value,
        email: $("email").value,
        phone: $("phone").value,
        address: $("address").value,
        company: $("company").value
    };

    try {
        await request(id ? `/contacts/${id}` : "/contacts", {
            method: id ? "PUT" : "POST",
            body: JSON.stringify(body)
        });

        closeModal();
        showToast(id ? "Contact updated successfully" : "Contact added successfully");

        loadContacts();
        loadDashboard();
    } catch (error) {
        showToast(error.message, true);
    }
});

async function deleteContact(id) {
    if (!confirm("Are you sure you want to delete this contact?")) {
        return;
    }

    try {
        await request(`/contacts/${id}`, {
            method: "DELETE"
        });

        showToast("Contact deleted successfully");
        loadContacts();
        loadDashboard();
    } catch (error) {
        showToast(error.message, true);
    }
}

$("modal").addEventListener("click", event => {
    if (event.target === $("modal")) {
        closeModal();
    }
});

loadDashboard();
