const api = "/api";
let cache = {books:[], members:[], authors:[]};

async function request(url, options={}) {
  const res = await fetch(api + url, {headers: {"Content-Type":"application/json"}, ...options});
  const data = await res.json().catch(()=>({success:false,message:"Invalid server response"}));
  if (!res.ok || data.success === false) throw new Error(data.message || "Request failed");
  return data;
}
function toast(msg, good=true){const t=document.getElementById("toast");t.textContent=msg;t.style.display="block";t.style.background=good?"#111827":"#b91c1c";setTimeout(()=>t.style.display="none",2600)}
function openModal(id){document.getElementById(id).classList.add("show")}
function closeModal(id){document.getElementById(id).classList.remove("show")}
function go(page){
  document.querySelectorAll(".page").forEach(x=>x.classList.remove("active"));
  document.getElementById(page).classList.add("active");
  document.querySelectorAll(".nav-btn").forEach(x=>x.classList.toggle("active",x.dataset.page===page));
  const titles={dashboard:["Dashboard","Library overview and quick actions"],books:["Books","Manage books, availability and inventory"],members:["Members","Manage library members"],authors:["Authors","Manage authors"],issues:["Borrow / Return","Track issued and returned books"],reports:["Reports","Library statistics and overdue information"]};
  document.getElementById("pageTitle").textContent=titles[page][0];
  document.getElementById("pageSub").textContent=titles[page][1];
  if(page==="books")loadBooks(); if(page==="members")loadMembers(); if(page==="authors")loadAuthors(); if(page==="issues")loadIssues(); if(page==="reports")loadReports(); if(page==="dashboard")loadDashboard();
}
document.querySelectorAll(".nav-btn").forEach(b=>b.addEventListener("click",()=>go(b.dataset.page)));
document.getElementById("mobileMenu").onclick=()=>document.querySelector(".sidebar").classList.toggle("open");

function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
function empty(msg="No records found"){return `<div class="empty">${msg}</div>`}

async function loadDashboard(){
  try{
    const [b,m,i,r]=await Promise.all([request("/books?limit=100"),request("/members?limit=100"),request("/issues?limit=100"),request("/reports")]);
    cache.books=b.data.data; cache.members=m.data.data;
    document.getElementById("sBooks").textContent=r.data.totalBooks;
    document.getElementById("sMembers").textContent=r.data.totalMembers;
    document.getElementById("sAvailable").textContent=r.data.availableCopies;
    document.getElementById("sIssued").textContent=r.data.activeIssues;
    document.getElementById("recentBooks").innerHTML=renderBooks(cache.books.slice(-5).reverse(),true);
  }catch(e){toast(e.message,false)}
}

async function loadAuthors(){
  try{
    const search=document.getElementById("authorSearch").value;
    const r=await request("/authors?limit=100&search="+encodeURIComponent(search));
    cache.authors=r.data.data;
    document.getElementById("authorsTable").innerHTML=cache.authors.length?`<table><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Actions</th></tr></thead><tbody>${cache.authors.map(a=>`<tr><td>#${a.id}</td><td><b>${esc(a.name)}</b></td><td>${esc(a.email)}</td><td><button class="action danger" onclick="deleteAuthor(${a.id})">Delete</button></td></tr>`).join("")}</tbody></table>`:empty();
    fillAuthorSelect();
  }catch(e){toast(e.message,false)}
}
function fillAuthorSelect(){document.getElementById("bookAuthor").innerHTML=cache.authors.map(a=>`<option value="${a.id}">${esc(a.name)}</option>`).join("")}

async function loadBooks(){
  try{
    const search=document.getElementById("bookSearch").value;
    const category=document.getElementById("bookCategory").value;
    const av=document.getElementById("availableOnly").checked;
    let q=`/books?limit=100&search=${encodeURIComponent(search)}`;
    if(category)q+=`&category=${encodeURIComponent(category)}`; if(av)q+="&available=true";
    const r=await request(q); cache.books=r.data.data;
    const cats=[...new Set(cache.books.map(b=>b.category))];
    const sel=document.getElementById("bookCategory"); const old=sel.value;
    if(sel.options.length===1)cats.forEach(c=>{const o=document.createElement("option");o.value=c;o.textContent=c;sel.appendChild(o)});
    sel.value=old;
    document.getElementById("booksTable").innerHTML=renderBooks(cache.books,false);
  }catch(e){toast(e.message,false)}
}
function renderBooks(items,compact){
  if(!items.length)return empty();
  return `<table><thead><tr><th>Book</th><th>Author</th><th>Category</th><th>Copies</th><th>Status</th>${compact?"":"<th>Actions</th>"}</tr></thead><tbody>${items.map(b=>`<tr><td><b>${esc(b.title)}</b><br><small>${esc(b.isbn)}</small></td><td>${esc(b.author?.name||"Unknown")}</td><td>${esc(b.category)}</td><td>${b.availableCopies}/${b.totalCopies}</td><td><span class="badge ${b.availableCopies?"available":"unavailable"}">${b.availableCopies?"Available":"Unavailable"}</span></td>${compact?"":`<td><button class="action" onclick="editBook(${b.id})">Edit</button><button class="action danger" onclick="deleteBook(${b.id})">Delete</button></td>`}</tr>`).join("")}</tbody></table>`
}

async function loadMembers(){
  try{
    const search=document.getElementById("memberSearch").value;
    const r=await request("/members?limit=100&search="+encodeURIComponent(search)); cache.members=r.data.data;
    document.getElementById("membersTable").innerHTML=cache.members.length?`<table><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Phone</th><th>Type</th><th>Actions</th></tr></thead><tbody>${cache.members.map(m=>`<tr><td>#${m.id}</td><td><b>${esc(m.name)}</b></td><td>${esc(m.email)}</td><td>${esc(m.phone)}</td><td>${esc(m.membershipType)}</td><td><button class="action danger" onclick="deleteMember(${m.id})">Delete</button></td></tr>`).join("")}</tbody></table>`:empty();
  }catch(e){toast(e.message,false)}
}

async function loadIssues(){
  try{
    const status=document.getElementById("issueStatus").value;
    const r=await request("/issues?limit=100"+(status?"&status="+status:""));
    const items=r.data.data;
    document.getElementById("issuesTable").innerHTML=items.length?`<table><thead><tr><th>Book</th><th>Member</th><th>Issue Date</th><th>Due Date</th><th>Status</th><th>Fee</th><th>Action</th></tr></thead><tbody>${items.map(i=>`<tr><td>${esc(i.book?.title||"Deleted")}</td><td>${esc(i.member?.name||"Deleted")}</td><td>${date(i.issueDate)}</td><td>${date(i.dueDate)}</td><td><span class="badge ${i.status}">${esc(i.status)}</span>${i.overdueDays?` <span class="badge overdue">${i.overdueDays}d overdue</span>`:""}</td><td>₹${i.lateFee}</td><td>${i.status==="issued"?`<button class="action" onclick="returnBook(${i.id})">Return</button>`:"—"}</td></tr>`).join("")}</tbody></table>`:empty("No borrowing records");
  }catch(e){toast(e.message,false)}
}
function date(x){return x?new Date(x).toLocaleDateString("en-IN"):"—"}

async function loadReports(){
  try{
    const r=await request("/reports"); const x=r.data;
    document.getElementById("rBooks").textContent=x.totalBooks;
    document.getElementById("rCopies").textContent=x.totalCopies;
    document.getElementById("rOverdue").textContent=x.overdueBooks;
    document.getElementById("rFees").textContent="₹"+x.estimatedLateFees;
    document.getElementById("reportContent").innerHTML=[
      ["Total authors",x.totalAuthors],["Total members",x.totalMembers],["Available copies",x.availableCopies],
      ["Borrowed copies",x.borrowedCopies],["Active issues",x.activeIssues],["Returned books",x.returnedBooks]
    ].map(a=>`<div class="report-item"><small>${a[0]}</small><b>${a[1]}</b></div>`).join("");
    document.getElementById("overdueTable").innerHTML=x.overdueRecords.length?`<table><thead><tr><th>Book ID</th><th>Member ID</th><th>Due Date</th><th>Overdue Days</th><th>Late Fee</th></tr></thead><tbody>${x.overdueRecords.map(i=>`<tr><td>#${i.bookId}</td><td>#${i.memberId}</td><td>${date(i.dueDate)}</td><td>${i.overdueDays}</td><td>₹${i.lateFee}</td></tr>`).join("")}</tbody></table>`:empty("🎉 No overdue books");
  }catch(e){toast(e.message,false)}
}

document.getElementById("authorForm").onsubmit=async e=>{
  e.preventDefault();
  try{await request("/authors",{method:"POST",body:JSON.stringify({name:authorName.value,email:authorEmail.value})});closeModal("authorModal");e.target.reset();toast("Author added successfully");loadAuthors();loadDashboard()}catch(x){toast(x.message,false)}
};
document.getElementById("memberForm").onsubmit=async e=>{
  e.preventDefault();
  try{await request("/members",{method:"POST",body:JSON.stringify({name:memberName.value,email:memberEmail.value,phone:memberPhone.value,membershipType:memberType.value})});closeModal("memberModal");e.target.reset();toast("Member added successfully");loadMembers();loadDashboard()}catch(x){toast(x.message,false)}
};
document.getElementById("bookForm").onsubmit=async e=>{
  e.preventDefault();
  try{
    const id=bookId.value;
    const body={title:bookTitle.value,isbn:bookIsbn.value,authorId:Number(bookAuthor.value),category:bookCategoryInput.value,year:Number(bookYear.value),totalCopies:Number(bookCopies.value)};
    await request(id?"/books/"+id:"/books",{method:id?"PUT":"POST",body:JSON.stringify(body)});
    closeModal("bookModal");e.target.reset();bookId.value="";bookModalTitle.textContent="Add Book";toast(id?"Book updated successfully":"Book added successfully");loadBooks();loadDashboard();
  }catch(x){toast(x.message,false)}
};
document.getElementById("issueForm").onsubmit=async e=>{
  e.preventDefault();
  try{await request("/issues",{method:"POST",body:JSON.stringify({bookId:Number(issueBook.value),memberId:Number(issueMember.value),days:Number(issueDays.value)})});closeModal("issueModal");toast("Book issued successfully");loadIssues();loadBooks();loadDashboard()}catch(x){toast(x.message,false)}
};

async function deleteAuthor(id){if(!confirm("Delete this author?"))return;try{await request("/authors/"+id,{method:"DELETE"});toast("Author deleted");loadAuthors()}catch(e){toast(e.message,false)}}
async function deleteMember(id){if(!confirm("Delete this member?"))return;try{await request("/members/"+id,{method:"DELETE"});toast("Member deleted");loadMembers();loadDashboard()}catch(e){toast(e.message,false)}}
async function deleteBook(id){if(!confirm("Delete this book?"))return;try{await request("/books/"+id,{method:"DELETE"});toast("Book deleted");loadBooks();loadDashboard()}catch(e){toast(e.message,false)}}
async function editBook(id){
  try{
    const r=await request("/books/"+id),b=r.data; bookId.value=b.id;bookTitle.value=b.title;bookIsbn.value=b.isbn;bookAuthor.value=b.authorId;bookCategoryInput.value=b.category;bookYear.value=b.year;bookCopies.value=b.totalCopies;bookModalTitle.textContent="Edit Book";openModal("bookModal");
  }catch(e){toast(e.message,false)}
}
async function returnBook(id){if(!confirm("Return this book?"))return;try{const r=await request("/issues/"+id+"/return",{method:"PUT"});toast(`Returned. Late fee: ₹${r.data.lateFee}`);loadIssues();loadBooks();loadDashboard();}catch(e){toast(e.message,false)}}
async function openIssueModal(){
  try{
    const [b,m]=await Promise.all([request("/books?limit=100&available=true"),request("/members?limit=100")]);
    document.getElementById("issueBook").innerHTML=b.data.data.map(x=>`<option value="${x.id}">${esc(x.title)} — ${x.availableCopies} available</option>`).join("");
    document.getElementById("issueMember").innerHTML=m.data.data.map(x=>`<option value="${x.id}">${esc(x.name)} — ${esc(x.membershipType)}</option>`).join("");
    openModal("issueModal");
  }catch(e){toast(e.message,false)}
}

window.onclick=e=>{if(e.target.classList.contains("modal"))e.target.classList.remove("show")}
loadDashboard();
