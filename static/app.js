const $ = s => document.querySelector(s);
const PALETTE = ["#3E8E41","#7BB33A","#C8423B","#4A90D9","#C98A2E","#1FA3A3","#8A7FA8","#D4537E","#E07B24","#5B6BD6","#2E8B6E","#9C6B3F"];
let cats = [], items = [], learned = [], current = null, view = "list", filter = "";
let sugs = [], shownSugs = [], hl = -1, hist = [], appVersion = "";

let lists = [], listId = null, info = null, me = null;
const L = path => `/api/lists/${listId}${path}`;
const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } },
                set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json", "X-Requested-With": "boodschappen" }, ...opts });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) { location.reload(); throw new Error("uitgelogd"); }
  if (data.code === "not_member") { listGone(); throw new Error(data.error); }
  if (!res.ok) { toast(data.error || "Opslaan lukte niet. Probeer het opnieuw."); throw new Error(data.error); }
  return data;
}
const esc = s => { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; };
const catOf = key => cats.find(c => c.key === key) || cats[cats.length - 1];
let toastT;
/* ---------- ongedaan maken: één balk voor alles wat je net hebt afgevinkt ---------- */
let pending = [], undoT, undoOpen = false;
const UNDO_MS = 6000;
function undoBottom() {
  const form = $("#form"), formH = getComputedStyle(form).display === "none" ? 0 : form.offsetHeight;
  return formH ? `${formH + 10}px` : "";
}
function renderUndo() {
  const u = $("#undo");
  if (!pending.length) { u.classList.remove("show", "counting", "open"); undoOpen = false; return; }
  const one = pending.length === 1;
  $("#undoMsg").textContent = one ? `${pending[0].name} afgevinkt` : `${pending.length} producten afgevinkt`;
  $("#undoChev").hidden = one;
  $("#undoSum").disabled = one;
  $("#undoSum").setAttribute("aria-expanded", undoOpen);
  $("#undoAll").textContent = one ? "Ongedaan maken" : "Alles terug";
  $("#undoList").innerHTML = pending.map((p, i) => `<li><span>${esc(p.name)}</span><button data-undo="${i}" aria-label="${esc(p.name)} terugzetten">Terug</button></li>`).join("");
  u.classList.toggle("open", undoOpen && !one);
  u.style.bottom = undoBottom();
  u.classList.add("show");
}
function restartUndoTimer() {
  const u = $("#undo");
  clearTimeout(undoT);
  u.classList.remove("counting"); void u.offsetWidth;
  u.style.setProperty("--dur", UNDO_MS + "ms");
  if (undoOpen) return; // uitgeklapt: blijft staan tot je hem weer inklapt
  u.classList.add("counting");
  undoT = setTimeout(() => { pending = []; renderUndo(); }, UNDO_MS);
}
function addPending(name, pid) {
  pending.push({ name, pid });
  renderUndo(); restartUndoTimer();
}
async function undoMany(list) {
  for (const p of list) items = await api(L(`/history/${p.pid}/undo`), { method: "POST" });
  pending = pending.filter(p => !list.includes(p));
  render(); renderUndo(); if (pending.length) restartUndoTimer();
}
$("#undoSum").onclick = () => { if (pending.length < 2) return; undoOpen = !undoOpen; renderUndo(); restartUndoTimer(); };
$("#undoAll").onclick = () => { clearTimeout(undoT); undoOpen = false; undoMany([...pending]); };
$("#undoList").addEventListener("click", e => { const b = e.target.closest("[data-undo]"); if (b) undoMany([pending[+b.dataset.undo]]); });

function toast(msg, action) {
  const t = $("#toast"), b = $("#toastBtn"), timer = $("#toastTimer"), ms = action ? 5000 : 2600;
  $("#toastMsg").textContent = msg;
  b.hidden = timer.hidden = !action;
  if (action) { b.textContent = action.label; b.onclick = () => { t.classList.remove("show"); action.run(); }; }
  // net boven het invoerveld (en de suggesties) zweven, niet midden in de lijst
  const form = $("#form"), formH = getComputedStyle(form).display === "none" ? 0 : form.offsetHeight;
  const u = $("#undo"), undoH = u.classList.contains("show") ? u.offsetHeight + 8 : 0;
  t.style.bottom = formH || undoH ? `${formH + 10 + undoH}px` : "";
  t.classList.remove("counting"); void t.offsetWidth;
  t.style.setProperty("--dur", ms + "ms");
  t.classList.add("show"); if (action) t.classList.add("counting");
  clearTimeout(toastT);
  toastT = setTimeout(() => t.classList.remove("show", "counting"), ms);
}

/* ---------- lijst ---------- */
function renderList() {
  $("#count").textContent = items.length ? `${items.length} te halen` : "";
  if (!items.length) {
    $("#main").innerHTML = `<div class="empty"><strong>Je lijst is leeg</strong>Typ hieronder wat je nodig hebt. Het komt vanzelf in de juiste volgorde te staan. Wat je afvinkt, vind je terug onder Historie.</div>`;
    return;
  }
  let html = '<div class="route">';
  for (const c of cats) {
    const group = items.filter(i => i.category === c.key);
    if (!group.length) continue;
    html += `<section class="stop" style="--cat:${c.color}"><h2>${esc(c.label)}</h2><ul class="list">`;
    for (const i of group) html += `<li data-li="${i.id}">
        <button class="check" data-toggle="${i.id}" aria-label="${esc(i.name)} afvinken"><span class="box"></span><span class="name">${esc(i.name)}</span></button>
        <button class="more" data-more="${i.id}" aria-label="Categorie wijzigen voor ${esc(i.name)}">⋯</button></li>`;
    html += "</ul></section>";
  }
  html += "</div>";
  $("#main").innerHTML = html;
}

/* ---------- aanpassen ---------- */
function renderSettings() {
  $("#count").textContent = "";
  const catRows = cats.map((c, i) => {
    const fixed = c.key === "overig";
    return `<li style="--cat:${c.color}">
      <button class="sw" data-color="${i}" aria-label="Andere kleur voor ${esc(c.label)}"></button>
      <input value="${esc(c.label)}" data-label="${i}" aria-label="Naam van categorie">
      <button class="ic" data-up="${i}" ${i === 0 ? "disabled" : ""} aria-label="Eerder in de route">↑</button>
      <button class="ic" data-down="${i}" ${i === cats.length - 1 ? "disabled" : ""} aria-label="Later in de route">↓</button>
      <button class="ic x" data-delcat="${i}" ${fixed ? "disabled" : ""} aria-label="Categorie verwijderen">✕</button></li>`;
  }).join("");
  const opts = sel => cats.map(c => `<option value="${c.key}"${c.key === sel ? " selected" : ""}>${esc(c.label)}</option>`).join("");
  const shown = learned.filter(l => l.name.includes(filter.toLowerCase()));
  const learnedRows = shown.length ? shown.map(l => `<li style="--cat:${catOf(l.category).color}">
      <span class="lname">${esc(l.name)}</span>
      <select data-learn="${esc(l.name)}" aria-label="Categorie voor ${esc(l.name)}" style="flex:0 1 46%">${opts(l.category)}</select>
      <button class="ic x" data-forget="${esc(l.name)}" aria-label="${esc(l.name)} vergeten">✕</button></li>`).join("")
    : `<li class="note">${learned.length ? "Geen product gevonden met die naam." : "Nog niets onthouden. Verplaats een product via ⋯ op je lijst, of voeg er hieronder een toe."}</li>`;

  const mine = info && info.role === "owner";
  const memberRows = info ? info.members.map(m => `<li>
      <span class="lname">${esc(m.name || m.email || "Onbekend")}${m.id === info.me ? " <small>(jij)</small>" : ""}
        ${m.name && m.email ? `<small class="sub">${esc(m.email)}</small>` : ""}</span>
      ${m.role === "owner" ? '<small class="tag">eigenaar</small>' : ""}
      ${mine && m.role !== "owner" ? `<button class="ic x" data-kick="${m.id}" aria-label="${esc(m.name || m.email)} van de lijst halen">✕</button>` : ""}</li>`).join("") : "";

  $("#main").innerHTML = `
    <section class="sec">
      <h2>Deze lijst</h2>
      <p>Iedereen op de lijst ziet dezelfde producten, looproute en historie, en kan alles aanpassen.</p>
      <div class="addrow" style="margin:0 0 12px"><input id="listName" value="${esc(info ? info.name : "")}" aria-label="Naam van de lijst"></div>
      <ul class="rows">${memberRows}</ul>
      <div class="addrow"><button class="btn" id="inviteBtn" style="flex:1;padding:12px">Iemand uitnodigen</button></div>
      <div id="inviteOut"></div>
      <div class="addrow"><button class="btn danger" id="${mine ? "delList" : "leaveList"}" style="flex:1;padding:12px">${mine ? "Lijst verwijderen" : "Stoppen met deze lijst"}</button></div>
    </section>
    <section class="sec">
      <h2>Looproute</h2>
      <p>Zet de categorieën in de volgorde waarin je door de winkel loopt. Tik op het bolletje voor een andere kleur.</p>
      <ul class="rows">${catRows}</ul>
      <div class="addrow"><input id="newCat" placeholder="Bijv. Diepvries" aria-label="Nieuwe categorie"><button class="btn" id="newCatBtn">Toevoegen</button></div>
    </section>
    <section class="sec">
      <h2>Onthouden producten</h2>
      <p>Hier staan producten die je zelf een plek hebt gegeven. Die keuze gaat altijd voor de automatische indeling.</p>
      <input class="filter" id="filter" placeholder="Zoek product" value="${esc(filter)}" aria-label="Zoek in onthouden producten">
      <ul class="rows">${learnedRows}</ul>
      <div class="addrow">
        <input id="newLearn" placeholder="Product, bijv. hummus" aria-label="Productnaam">
        <select id="newLearnCat" aria-label="Categorie" style="flex:0 1 40%">${opts("overig")}</select>
      </div>
      <div class="addrow"><button class="btn" id="newLearnBtn" style="flex:1;padding:12px">Product onthouden</button></div>
    </section>
    <section class="sec">
      <h2>Account</h2>
      <p>${me ? `Ingelogd als ${esc(me.name || me.email || "")}${me.email && me.name ? ` (${esc(me.email)})` : ""} via ${({ google: "Google", apple: "Apple", dev: "test-login" })[me.provider] || me.provider}.` : ""}</p>
      <div class="addrow" style="margin:0"><button class="btn" id="logout" style="flex:1;padding:12px">Uitloggen</button>
        <button class="btn danger" id="delAccount" style="flex:1;padding:12px">Account verwijderen</button></div>
    </section>
    <p class="ver">${appVersion ? (/^\d/.test(appVersion)
      ? `<a href="https://github.com/RichrdJ/boodschappenlijst/releases/tag/v${esc(appVersion)}" target="_blank" rel="noopener">Versie ${esc(appVersion)}</a>`
      : `Versie ${esc(appVersion)}`) : ""}</p>`;
}

/* ---------- historie ---------- */
const dayKey = ts => { const d = new Date(ts * 1000); return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`; };
function dayLabel(ts) {
  const d = new Date(ts * 1000), today = new Date(), y = new Date(); y.setDate(today.getDate() - 1);
  if (dayKey(ts) === dayKey(today / 1000)) return "Vandaag";
  if (dayKey(ts) === dayKey(y / 1000)) return "Gisteren";
  return d.toLocaleDateString("nl-NL", { weekday: "long", day: "numeric", month: "long", ...(d.getFullYear() !== today.getFullYear() && { year: "numeric" }) });
}
function renderHistory() {
  $("#count").textContent = "";
  if (!hist.length) {
    $("#main").innerHTML = `<div class="empty"><strong>Nog geen historie</strong>Vink iets af op je lijst, dan zie je het hier terug per dag.</div>`;
    return;
  }
  const days = [];
  for (const p of hist) {
    const k = dayKey(p.bought);
    if (!days.length || days[days.length - 1].key !== k) days.push({ key: k, ts: p.bought, rows: [] });
    days[days.length - 1].rows.push(p);
  }
  $("#main").innerHTML = days.map((d, di) => `<section class="day">
    <div class="day-h"><div><h2>${dayLabel(d.ts)}</h2><small>${d.rows.length} ${d.rows.length === 1 ? "product" : "producten"}</small></div>
      <button class="again" data-dayadd="${di}">Alles weer op de lijst</button></div>
    <ul class="rows">${d.rows.map(p => `<li class="hrow" style="--cat:${catOf(p.category).color}">
      <span class="dot" aria-hidden="true"></span>
      <span class="lname">${esc(p.name)}</span>
      <span class="t">${new Date(p.bought * 1000).toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" })}</span>
      <button class="ic plus" data-readd="${p.id}" aria-label="${esc(p.name)} weer op de lijst">+</button>
      <button class="ic x" data-hdel="${p.id}" aria-label="${esc(p.name)} uit historie verwijderen">✕</button></li>`).join("")}</ul>
  </section>`).join("");
  window._days = days;
}
async function readd(names) {
  const r = await api(L("/history/readd"), { method: "POST", body: JSON.stringify({ names }) });
  items = r.items;
  if (!r.added) toast(names.length === 1 ? `${names[0]} staat al op je lijst` : "Alles staat al op je lijst");
  else toast(names.length === 1 ? `${names[0]} staat weer op je lijst` : `${r.added} ${r.added === 1 ? "product" : "producten"} weer op je lijst`);
}

function render() { ({ list: renderList, history: renderHistory, settings: renderSettings })[view](); }

async function saveCats() { cats = await api(L("/categories"), { method: "PUT", body: JSON.stringify(cats) }); render(); }

/* ---------- data ---------- */
async function load() {
  try { [cats, items] = await Promise.all([api(L("/categories")), api(L("/items"))]); if (view === "list") render(); } catch (e) {}
}
async function loadSuggestions() {
  try { sugs = await api(L("/suggestions")); renderSugs(); } catch (e) {}
}

/* ---------- herkenning: eerder getypte producten ---------- */
const norm = s => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/^\s*\d+[.,]?\d*\s*(x|st|stuks|kg|g|gr|gram|l|liter|ml|pak|zak|bos)?\s+/, "").trim();
const onList = name => items.some(i => norm(i.name) === norm(name));

function matchScore(name, q) {
  const n = norm(name);
  if (n === q) return 100;
  if (n.startsWith(q)) return 80;
  if (n.split(/[\s-]+/).some(w => w.startsWith(q))) return 60;
  if (n.includes(q)) return 30;
  return 0;
}

function renderSugs() {
  const raw = $("#input").value, q = norm(raw);
  if (!q) {
    // Leeg invoerveld: laat zien wat je vaak koopt en nog niet op de lijst staat
    shownSugs = document.activeElement === $("#input") ? sugs.filter(s => !onList(s.name)).slice(0, 8) : [];
  } else {
    shownSugs = sugs.map(s => ({ ...s, score: matchScore(s.name, q) }))
      .filter(s => s.score > 0 && !(s.score === 100 && raw.trim() === s.name))
      .sort((a, b) => b.score - a.score || b.uses - a.uses).slice(0, 6);
  }
  hl = Math.min(hl, shownSugs.length - 1);
  const label = !q && shownSugs.length ? '<span class="sug-label">Vaak gekocht</span>' : "";
  $("#sugs").innerHTML = label + shownSugs.map((s, i) => {
    const c = catOf(s.category), n = esc(s.name);
    const t = raw.trim().toLowerCase(), idx = t ? s.name.toLowerCase().indexOf(t) : -1;
    const shown = idx >= 0 ? esc(s.name.slice(0, idx)) + "<b>" + esc(s.name.slice(idx, idx + t.length)) + "</b>" + esc(s.name.slice(idx + t.length)) : n;
    return `<span class="chip${i === hl ? " hl" : ""}${onList(s.name) ? " on-list" : ""}" role="option" aria-selected="${i === hl}">
      <button type="button" class="chip-add" data-sug="${i}" style="--cat:${c.color}" aria-label="${n} toevoegen${onList(s.name) ? ", staat al op je lijst" : ""}"><i></i><span>${shown}</span></button>
      <button type="button" class="chip-x" data-sugdel="${i}" aria-label="${n} niet meer voorstellen">✕</button></span>`;
  }).join("");
}

async function addItem(name) {
  if (onList(name)) { toast(`${name} staat al op je lijst`); return; }
  items = await api(L("/items"), { method: "POST", body: JSON.stringify({ name }) });
  const added = items[items.map(i => i.name).lastIndexOf(name)];
  if (added) toast(`${name} staat bij ${catOf(added.category).label}`);
  render(); loadSuggestions();
}

$("#input").addEventListener("input", () => { hl = -1; renderSugs(); });
$("#input").addEventListener("focus", renderSugs);
$("#input").addEventListener("blur", () => setTimeout(() => { if (document.activeElement?.closest?.("#sugs")) return; if (!$("#input").value) { shownSugs = []; $("#sugs").innerHTML = ""; } }, 150));
$("#input").addEventListener("keydown", e => {
  if (!shownSugs.length) return;
  if (e.key === "ArrowDown" || e.key === "ArrowRight" && hl >= 0) { e.preventDefault(); hl = (hl + 1) % shownSugs.length; renderSugs(); }
  else if (e.key === "ArrowUp" || e.key === "ArrowLeft" && hl >= 0) { e.preventDefault(); hl = (hl - 1 + shownSugs.length) % shownSugs.length; renderSugs(); }
  else if (e.key === "Tab" && $("#input").value) { e.preventDefault(); $("#input").value = shownSugs[Math.max(hl, 0)].name; hl = -1; renderSugs(); }
  else if (e.key === "Escape") { hl = -1; $("#sugs").innerHTML = ""; shownSugs = []; }
});
$("#sugs").addEventListener("pointerdown", e => e.preventDefault()); // toetsenbord blijft open
$("#sugs").addEventListener("click", async e => {
  const b = e.target.closest("button"); if (!b) return;
  if (b.dataset.sug !== undefined) {
    const s = shownSugs[+b.dataset.sug]; $("#input").value = ""; hl = -1;
    await addItem(s.name); $("#input").focus(); renderSugs();
  } else if (b.dataset.sugdel !== undefined) {
    const s = shownSugs[+b.dataset.sugdel];
    sugs = await api(L(`/suggestions/${encodeURIComponent(s.name)}`), { method: "DELETE" });
    renderSugs(); toast(`${s.name} wordt niet meer voorgesteld`);
  }
});

/* ---------- events ---------- */
async function setView(v) {
  view = v;
  document.querySelectorAll(".tab").forEach(t => t.setAttribute("aria-selected", t.dataset.view === v));
  document.body.classList.toggle("settings", v !== "list");
  if (v === "settings") learned = await api(L("/learned"));
  if (v === "settings") await loadListInfo();
  if (v === "history") hist = await api(L("/history"));
  if (v === "list") items = await api(L("/items"));
  render(); renderUndo(); window.scrollTo(0, 0);
}
document.querySelectorAll(".tab").forEach(t => t.onclick = () => setView(t.dataset.view));

$("#form").addEventListener("submit", async e => {
  e.preventDefault();
  const name = hl >= 0 && shownSugs[hl] ? shownSugs[hl].name : $("#input").value.trim();
  if (!name) return;
  $("#input").value = ""; hl = -1;
  await addItem(name); renderSugs();
});

$("#main").addEventListener("click", async e => {
  const d = e.target.closest("button")?.dataset || {};
  if (d.toggle) {
    const it = items.find(i => i.id == d.toggle);
    const li = it && document.querySelector(`[data-li="${it.id}"]`);
    if (!li || li.classList.contains("leaving")) return;
    li.classList.add("checked", "leaving");
    const req = api(L(`/items/${it.id}`), { method: "PATCH", body: JSON.stringify({ checked: true }) });
    await new Promise(r => setTimeout(r, 450));
    const r = await req; items = r.items; render();
    addPending(it.name, r.purchase_id);
  } else if (d.more) {
    current = items.find(i => i.id == d.more); openSheet();
  } else if (d.readd) {
    await readd([hist.find(p => p.id == d.readd).name]);
  } else if (d.dayadd) {
    await readd([...new Set(window._days[+d.dayadd].rows.map(p => p.name))]);
  } else if (d.hdel) {
    hist = await api(L(`/history/${d.hdel}`), { method: "DELETE" }); render();
  } else if (d.up || d.down) {
    const i = +(d.up ?? d.down), j = d.up ? i - 1 : i + 1;
    [cats[i], cats[j]] = [cats[j], cats[i]]; await saveCats();
    document.querySelector(`[data-${d.up ? "up" : "down"}="${j}"]`)?.focus();
  } else if (d.color) {
    const c = cats[+d.color]; c.color = PALETTE[(PALETTE.indexOf(c.color) + 1) % PALETTE.length]; await saveCats();
  } else if (d.delcat) {
    const c = cats[+d.delcat];
    if (!confirm(`${c.label} verwijderen? Producten in deze categorie gaan naar Overig.`)) return;
    cats.splice(+d.delcat, 1); await saveCats(); learned = await api(L("/learned")); render(); toast(`${c.label} verwijderd`);
  } else if (d.forget) {
    learned = await api(L(`/learned/${encodeURIComponent(d.forget)}`), { method: "DELETE" }); render(); toast(`${d.forget} vergeten`);
  } else if (d.kick) {
    const m = info.members.find(x => x.id == d.kick);
    if (!confirm(`${m.name || m.email} van deze lijst halen?`)) return;
    info = await api(L(`/members/${m.id}`), { method: "DELETE" }); render(); toast(`${m.name || m.email} doet niet meer mee`);
  } else if (e.target.id === "inviteBtn") {
    await invite();
  } else if (e.target.id === "copyInvite") {
    copyInvite();
  } else if (e.target.id === "leaveList") {
    if (!confirm(`Stoppen met ${info.name}? Je kunt alleen terug met een nieuwe uitnodiging.`)) return;
    await api(L(`/members/${info.me}`), { method: "DELETE" }); toast(`Je doet niet meer mee met ${info.name}`); await listGone();
  } else if (e.target.id === "delList") {
    const others = info.members.length - 1;
    if (!confirm(`${info.name} verwijderen?${others ? ` Ook de ${others === 1 ? "ander" : `${others} anderen`} op de lijst ${others === 1 ? "raakt" : "raken"} hem kwijt.` : ""} Dit kan niet ongedaan worden.`)) return;
    await api(L(""), { method: "DELETE" }); toast(`${info.name} verwijderd`); await listGone();
  } else if (e.target.id === "logout") {
    await api("/api/logout", { method: "POST" }); location.href = "/";
  } else if (e.target.id === "delAccount") {
    if (!confirm("Je account verwijderen? Lijsten waar jij eigenaar van bent verdwijnen, ook voor wie meedoet.")) return;
    await api("/api/me", { method: "DELETE" }); location.href = "/";
  } else if (e.target.id === "newCatBtn") {
    const label = $("#newCat").value.trim(); if (!label) return toast("Geef de categorie een naam");
    cats = await api(L("/categories"), { method: "POST", body: JSON.stringify({ label }) }); render(); toast(`${label} toegevoegd`);
  } else if (e.target.id === "newLearnBtn") {
    const name = $("#newLearn").value.trim(); if (!name) return toast("Vul een productnaam in");
    learned = await api(L("/learned"), { method: "PUT", body: JSON.stringify({ name, category: $("#newLearnCat").value }) });
    render(); toast(`${name} onthouden`);
  }
});

$("#main").addEventListener("change", async e => {
  const d = e.target.dataset;
  if (e.target.id === "listName") {
    const name = e.target.value.trim(); if (!name) { e.target.value = info.name; return toast("Geef de lijst een naam"); }
    info = await api(L(""), { method: "PATCH", body: JSON.stringify({ name }) }); await loadLists(); toast("Naam opgeslagen");
  }
  if (d.label !== undefined) { cats[+d.label].label = e.target.value; await saveCats(); toast("Naam opgeslagen"); }
  if (d.learn) {
    learned = await api(L("/learned"), { method: "PUT", body: JSON.stringify({ name: d.learn, category: e.target.value }) });
    render(); toast(`${d.learn} staat nu bij ${catOf(e.target.value).label}`);
  }
});
$("#main").addEventListener("input", e => {
  if (e.target.id === "filter") { filter = e.target.value; const pos = e.target.selectionStart; render(); const f = $("#filter"); f.focus(); f.setSelectionRange(pos, pos); }
});
$("#main").addEventListener("keydown", e => {
  if (e.key !== "Enter") return;
  if (e.target.id === "newCat") $("#newCatBtn").click();
  if (e.target.id === "listName") e.target.blur();
  if (e.target.id === "newLearn") $("#newLearnBtn").click();
});

/* ---------- sheet ---------- */
function openSheet() {
  $("#sheetTitle").textContent = current.name;
  $("#opts").innerHTML = cats.map(c => `<button class="opt${c.key === current.category ? " on" : ""}" data-cat="${c.key}" style="--cat:${c.color}"><i></i>${esc(c.label)}</button>`).join("");
  $("#newCatSheet").value = "";
  if (!$("#sheet").open) $("#sheet").showModal();
}
async function moveTo(key) {
  items = await api(L(`/items/${current.id}`), { method: "PATCH", body: JSON.stringify({ category: key }) });
  $("#sheet").close(); render(); toast(`Onthouden: ${current.name} hoort bij ${catOf(key).label}`);
}
$("#opts").addEventListener("click", e => { const b = e.target.closest("[data-cat]"); if (b) moveTo(b.dataset.cat); });
$("#newCatSheetBtn").onclick = async () => {
  const label = $("#newCatSheet").value.trim(); if (!label) return toast("Geef de categorie een naam");
  const before = new Set(cats.map(c => c.key));
  cats = await api(L("/categories"), { method: "POST", body: JSON.stringify({ label }) });
  await moveTo(cats.find(c => !before.has(c.key)).key);
};
$("#newCatSheet").addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); $("#newCatSheetBtn").click(); } });
$("#del").onclick = async () => { items = await api(L(`/items/${current.id}`), { method: "DELETE" }); $("#sheet").close(); render(); };
$("#cancel").onclick = () => $("#sheet").close();

/* ---------- lijsten: wisselen, delen ---------- */
function renderHeader() {
  const l = lists.find(x => x.id === listId);
  $("#listTitle").textContent = l ? l.name : "Boodschappen";
  document.title = l ? l.name : "Boodschappen";
  const others = info && info.id === listId ? info.members.filter(m => m.id !== info.me) : [];
  $("#together").textContent = others.length ? `Samen met ${others.map(m => (m.name || m.email || "").split(" ")[0]).join(", ")}` : "";
}
async function loadLists() {
  lists = await api("/api/lists");
  renderHeader();
}
async function loadListInfo() {
  try { info = await api(L("")); renderHeader(); } catch (e) {}
}
async function selectList(id) {
  listId = id; store.set("list", id);
  info = null; pending = []; renderUndo(); sugs = []; renderSugs();
  renderHeader();
  await Promise.all([load(), loadListInfo()]); loadSuggestions();
  if (view !== "list") setView(view);
}
async function listGone() {
  await loadLists();
  await selectList(lists[0].id);
}
function renderListSheet() {
  $("#listOpts").innerHTML = lists.map(l => `<button class="lopt${l.id === listId ? " on" : ""}" data-list="${l.id}">
      <span><b>${esc(l.name)}</b><small>${l.members > 1 ? `Gedeeld · ${l.members} personen` : "Alleen jij"}</small></span>
      <small>${l.items ? `${l.items} te halen` : ""}</small></button>`).join("");
}
$("#listBtn").onclick = async () => {
  renderListSheet(); $("#newListName").value = ""; $("#lists").showModal();
  await loadLists(); renderListSheet();
};
$("#listOpts").addEventListener("click", async e => {
  const b = e.target.closest("[data-list]"); if (!b) return;
  $("#lists").close(); if (+b.dataset.list !== listId) await selectList(+b.dataset.list);
});
$("#newListBtn").onclick = async () => {
  const name = $("#newListName").value.trim(); if (!name) return toast("Geef de lijst een naam");
  const r = await api("/api/lists", { method: "POST", body: JSON.stringify({ name }) });
  lists = r.lists; $("#lists").close(); await selectList(r.id); toast(`${name} gemaakt`);
};
$("#newListName").addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); $("#newListBtn").click(); } });
$("#listsClose").onclick = () => $("#lists").close();

let inviteUrl = "";
async function invite() {
  const r = await api(L("/invites"), { method: "POST" });
  inviteUrl = r.url;
  const text = `Doe mee met mijn boodschappenlijst "${info.name}"`;
  $("#inviteOut").innerHTML = `<p class="note" style="padding:12px 0 0">Stuur deze link naar wie je wilt uitnodigen. Hij werkt één keer en is ${r.days} dagen geldig.</p>
    <div class="addrow"><input readonly value="${esc(inviteUrl)}" id="inviteUrl" aria-label="Uitnodigingslink"><button class="btn" id="copyInvite">Kopieer</button></div>`;
  if (navigator.share) {
    try { await navigator.share({ title: "Boodschappenlijst", text, url: inviteUrl }); } catch (e) {}
  }
}
async function copyInvite() {
  try { await navigator.clipboard.writeText(inviteUrl); toast("Link gekopieerd"); }
  catch (e) { const i = $("#inviteUrl"); i.focus(); i.select(); toast("Selecteer en kopieer de link"); }
}

(async () => {
  const params = new URLSearchParams(location.search);
  me = await api("/api/me");
  await loadLists();
  const want = +params.get("lijst") || +store.get("list");
  await selectList(lists.some(l => l.id === want) ? want : lists[0].id);
  if (params.get("welkom")) toast(`Je doet nu mee met ${lists.find(l => l.id === listId).name}`);
  if (params.get("uitnodiging")) toast("Die uitnodiging is verlopen of al gebruikt");
  if ([...params.keys()].length) history.replaceState(null, "", "/");
  api("/api/version").then(v => appVersion = v.version).catch(() => {});
  let tick = 0;
  setInterval(() => {
    if (document.hidden || $("#sheet").open || $("#lists").open || view !== "list") return;
    load(); if (++tick % 8 === 0) loadListInfo();
  }, 4000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden && view === "list") load(); });
})();
