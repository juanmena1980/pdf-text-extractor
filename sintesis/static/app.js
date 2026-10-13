const state = {
  tab: "desk",
  bootstrap: null,
  desk: null,
  notes: [],
  sends: [],
  clientId: null,
  edition: null,
  configId: null,
  editingId: null,
  busy: false,
  dragId: null,
};

const $ = (id) => document.getElementById(id);

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function br(value) {
  return esc(value).replace(/\n/g, "<br>");
}

function today() {
  const date = new Date();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

let toastTimer;
function toast(message) {
  const element = $("toast");
  element.hidden = false;
  element.textContent = message;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    element.hidden = true;
  }, 5200);
}

function ask(title, body, okLabel, showCancel = true) {
  const modal = $("modal");
  $("modalTitle").textContent = title;
  $("modalBody").textContent = body;
  $("modalOk").textContent = okLabel;
  $("modalCancel").hidden = !showCancel;
  modal.hidden = false;
  return new Promise((resolve) => {
    const form = $("modalForm");
    const onSubmit = (event) => {
      event.preventDefault();
      close(true);
    };
    const onCancel = () => close(false);
    const close = (value) => {
      modal.hidden = true;
      form.removeEventListener("submit", onSubmit);
      $("modalCancel").removeEventListener("click", onCancel);
      resolve(value);
    };
    form.addEventListener("submit", onSubmit);
    $("modalCancel").addEventListener("click", onCancel);
  });
}

function tell(title, body) {
  return ask(title, body, "Entendido", false);
}

async function api(path, options = {}) {
  const opts = { ...options, headers: { ...(options.headers || {}) } };
  if (opts.body && typeof opts.body !== "string") {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.body);
  }
  const response = await fetch(path, opts);
  const type = response.headers.get("content-type") || "";
  const data = type.includes("json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw new Error(data && data.error ? data.error : "No se pudo completar la acción.");
  }
  return data;
}

function remember() {
  if (state.clientId) localStorage.setItem("sintesis.clientId", String(state.clientId));
  if (state.edition) localStorage.setItem("sintesis.edition", state.edition);
}

function switchTab(tab) {
  state.tab = tab;
  for (const button of document.querySelectorAll("[data-tab]")) {
    button.classList.toggle("active", button.dataset.tab === tab);
  }
  $("view-desk").hidden = tab !== "desk";
  $("view-notes").hidden = tab !== "notes";
  $("view-sends").hidden = tab !== "sends";
  $("view-config").hidden = tab !== "config";
  if (tab === "desk") loadDesk();
  if (tab === "notes") {
    $("noteDate").value = state.editingId ? $("noteDate").value : state.edition;
    loadNotes();
  }
  if (tab === "sends") loadSends();
  if (tab === "config") renderConfig();
}

async function boot() {
  state.edition = localStorage.getItem("sintesis.edition") || today();
  const storedClient = Number(localStorage.getItem("sintesis.clientId") || 0);
  state.bootstrap = await api("/api/bootstrap");
  const params = new URLSearchParams(location.search);
  if (params.get("vista") === "config") state.tab = "config";
  const clients = state.bootstrap.clients;
  state.clientId = clients.some((client) => client.id === storedClient)
    ? storedClient
    : clients[0]?.id || null;
  state.configId = state.clientId;
  if (params.get("gmail") === "ok") toast("Cuenta de Gmail conectada. Asígnale un cliente.");
  if (params.get("gmail") === "error") {
    toast(state.bootstrap.oauth_error || "No se pudo conectar Gmail.");
  }
  if (params.get("gmail") || params.get("vista")) history.replaceState({}, "", "/");
  $("noteDate").value = state.edition;
  switchTab(state.tab);
  setStatus();
}

function setStatus() {
  const desk = state.desk;
  if (!desk) {
    $("statusLine").textContent = "Elige un cliente y arma la síntesis del día.";
    return;
  }
  const label = desk.synthesis ? desk.synthesis.status_label : "Sin armar";
  $("statusLine").textContent = `${desk.client.name} · ${label}`;
}

async function loadBootstrap() {
  state.bootstrap = await api("/api/bootstrap");
}

async function loadDesk() {
  if (!state.clientId) {
    renderDesk();
    setStatus();
    return;
  }
  state.desk = await api(`/api/desk?client_id=${state.clientId}&date=${state.edition}`);
  renderDesk();
  setStatus();
}

async function loadNotes() {
  const data = await api(`/api/notes?date=${state.edition}`);
  state.notes = data.notes;
  renderNotes();
}

async function loadSends() {
  const data = await api("/api/sends");
  state.sends = data.sends;
  renderSends();
}

function renderDesk() {
  const root = $("view-desk");
  const clients = state.bootstrap?.clients || [];
  if (!clients.length) {
    root.innerHTML = `<div class="panel empty">
      <h2>Arma la primera síntesis</h2>
      <p>Carga un día de ejemplo o crea un cliente con palabras clave, destinatarios y una hora de envío.</p>
      <div class="row-actions" style="justify-content:center">
        <button class="primary" type="button" data-action="example">Cargar un día de ejemplo</button>
        <button type="button" data-action="go-config">Crear cliente</button>
      </div>
    </div>`;
    return;
  }
  const desk = state.desk;
  if (!desk) {
    root.innerHTML = `<p class="loading">Cargando la mesa…</p>`;
    return;
  }
  const options = clients
    .map((client) => `<option value="${client.id}" ${client.id === state.clientId ? "selected" : ""}>${esc(client.name)}</option>`)
    .join("");
  const sections = desk.sections
    .map((section, index) => {
      const cards = section.items.map((item, itemIndex) => noteCard(item, itemIndex, desk.sections)).join("");
      return `<section class="section" data-index="${index}">
        <div class="section-head">
          <input class="section-name" value="${esc(section.name)}" aria-label="Nombre del grupo">
          <div class="row-actions">
            <button type="button" data-action="section-up" data-index="${index}">Subir grupo</button>
            <button type="button" data-action="section-down" data-index="${index}">Bajar grupo</button>
            <button type="button" data-action="section-delete" data-index="${index}" ${section.items.length ? "disabled" : ""}>Quitar grupo</button>
          </div>
        </div>
        ${cards || `<p class="help" style="padding:0.8rem">Arrastra notas aquí o créalas con las palabras clave.</p>`}
      </section>`;
    })
    .join("");
  const discarded = desk.discarded
    .map((item) => `<article class="note" data-item-id="${item.item_id}">
      <div class="note-rank" draggable="true">${esc(item.medium_label.slice(0, 1))}</div>
      <div>
        <div class="note-meta">${esc(item.outlet)}</div>
        <h3>${esc(item.title)}</h3>
        <button type="button" data-action="restore" data-item-id="${item.item_id}">Regresar a ${esc(item.section_name)}</button>
      </div>
    </article>`)
    .join("");
  const unassigned = desk.unassigned
    .map((note) => {
      const targets = desk.sections.map((section) => `<option value="${esc(section.name)}">${esc(section.name)}</option>`).join("");
      return `<article class="send-row">
        <div><strong>${esc(note.title)}</strong><div class="meta">${esc(note.medium_label)} · ${esc(note.outlet)}</div></div>
        <div class="row-actions">
          <select class="attach-section" data-note-id="${note.note_id}">
            <option value="General">General</option>
            ${targets}
          </select>
          <button type="button" data-action="attach" data-note-id="${note.note_id}">Agregar</button>
        </div>
      </article>`;
    })
    .join("");
  const checks = (desk.readiness?.checks || [])
    .map((check) => `<p class="check ${check.ok ? "ok" : "bad"}">${check.ok ? "●" : "○"} ${esc(check.label)}</p>`)
    .join("");
  const synthesis = desk.synthesis;
  const status = synthesis?.status || "borrador";
  let primary = `<button class="primary" type="button" data-action="review">Marcar revisada</button>`;
  if (status === "error") primary = `<button class="primary" type="button" data-action="retry">Reintentar envío</button>`;
  if (status === "enviada") primary = `<button class="primary" type="button" data-action="reopen">Abrir corrección</button>`;
  if (status === "enviando") primary = `<button class="primary" type="button" disabled>Enviando…</button>`;
  const preview = synthesis
    ? `<iframe class="preview" title="Vista previa del correo" sandbox src="/api/syntheses/${synthesis.id}/preview?v=${Date.now()}"></iframe>`
    : `<p class="help">La vista previa aparece cuando entra la primera nota.</p>`;
  root.innerHTML = `<div class="desk-grid">
    <div>
      <div class="toolbar">
        <div class="filters">
          <label>Cliente <select id="clientSelect">${options}</select></label>
          <label>Edición <input id="editionDate" type="date" value="${esc(state.edition)}"></label>
        </div>
        <div class="row-actions">
          <span class="pill ${esc(status)}">${esc(synthesis ? synthesis.status_label : "Sin armar")}</span>
          <button type="button" data-action="reclassify">Reclasificar</button>
          <button type="button" data-action="add-section" ${synthesis ? "" : "disabled"}>Nuevo grupo</button>
        </div>
      </div>
      ${synthesis?.error ? `<p class="warning">${esc(synthesis.error)}</p>` : ""}
      <div id="sectionList">${sections || `<div class="panel empty"><p>Todavía no hay grupos. Las palabras clave arman los grupos al entrar una nota.</p></div>`}</div>
      <section class="panel discard-bin">
        <h2>Descartadas (${desk.discarded.length})</h2>
        ${discarded || `<p class="help">Lo que descartes no sale en el correo.</p>`}
      </section>
    </div>
    <aside class="panel side">
      <p class="meta">Hora de envío ${esc(desk.client.send_time)} · se adelanta ${desk.plan.lead_minutes} minutos</p>
      <p class="plan">${esc(desk.plan_text)}</p>
      ${checks}
      <div class="row-actions">${primary}</div>
      <h3>Así saldrá el correo</h3>
      ${preview}
      <div class="unassigned">
        <h3>Notas de hoy fuera de esta síntesis</h3>
        ${unassigned || `<p class="help">No hay notas sueltas en esta fecha.</p>`}
      </div>
    </aside>
  </div>`;
}

function noteCard(item, index, sections) {
  const tag = item.match_phrase
    ? `palabra: ${item.match_phrase}`
    : item.origin === "manual"
      ? "colocada a mano"
      : "";
  const options = sections
    .filter((section) => section.name !== item.section_name)
    .map((section) => `<option value="${esc(section.name)}">${esc(section.name)}</option>`)
    .join("");
  return `<article class="note" data-item-id="${item.item_id}">
    <div class="note-rank" draggable="true" title="Arrastrar">${index + 1}</div>
    <div>
      <div class="note-meta"><span class="badge ${esc(item.medium)}">${esc(item.medium_label)}</span> ${esc(item.outlet)}${item.published_time ? ` · ${esc(item.published_time)}` : ""}</div>
      <h3>${esc(item.title)}</h3>
      ${tag ? `<p class="match">${esc(tag)}</p>` : ""}
      ${item.body ? `<details><summary>Leer</summary><p>${br(item.body)}</p></details>` : ""}
      <div class="note-actions">
        <button type="button" data-action="up" data-item-id="${item.item_id}">Subir</button>
        <button type="button" data-action="down" data-item-id="${item.item_id}">Bajar</button>
        <select class="move-section" data-item-id="${item.item_id}"><option value="">Mover a…</option>${options}</select>
        <button type="button" data-action="discard" data-item-id="${item.item_id}">Descartar</button>
      </div>
    </div>
  </article>`;
}

function renderNotes() {
  const list = $("noteList");
  if (!state.notes.length) {
    list.innerHTML = `<p class="help">No hay notas en esta fecha.</p>`;
    return;
  }
  list.innerHTML = state.notes
    .map((note) => {
      const places = (note.placements || [])
        .map((place) => `${place.client_name}: ${place.discarded ? "descartada" : place.section_name}`)
        .join(" · ");
      return `<article class="send-row">
        <div>
          <div class="note-meta"><span class="badge ${esc(note.medium)}">${esc(note.medium_label)}</span> ${esc(note.outlet)}</div>
          <strong>${esc(note.title)}</strong>
          <div class="meta">${esc(places || "Sin cliente")}</div>
        </div>
        <div class="row-actions">
          <button type="button" data-action="edit-note" data-note-id="${note.note_id}">Editar</button>
          <button type="button" data-action="delete-note" data-note-id="${note.note_id}">Borrar</button>
        </div>
      </article>`;
    })
    .join("");
}

function renderSends() {
  const root = $("view-sends");
  if (!state.sends.length) {
    root.innerHTML = `<div class="panel empty"><h2>Sin envíos</h2><p>Cuando marques una síntesis como revisada, aquí verás si quedó programada, enviada o con error.</p></div>`;
    return;
  }
  const rows = state.sends
    .map((item) => `<article class="send-row">
      <div>
        <strong>${esc(item.client_name)}</strong>
        <div class="meta">${esc(item.edition_date)} · ${esc(item.status_label)}${item.send_at ? ` · sale ${esc(item.send_at.slice(11, 16))}` : ""}${item.sent_at ? ` · enviado ${esc(item.sent_at.slice(11, 16))}` : ""}</div>
        ${item.error ? `<div class="check bad">${esc(item.error)}</div>` : ""}
      </div>
      <div class="row-actions">
        <button type="button" data-action="open-send" data-client-id="${item.client_id || ""}" data-date="${esc(item.edition_date)}">Abrir</button>
        ${item.status === "error" ? `<button class="primary" type="button" data-action="retry-send" data-synthesis-id="${item.id}">Reintentar</button>` : ""}
      </div>
    </article>`)
    .join("");
  root.innerHTML = `<div class="panel"><h2>Envíos</h2>${rows}</div>`;
}

function renderConfig() {
  const root = $("view-config");
  const data = state.bootstrap;
  if (!data) return;
  const accounts = data.accounts
    .map((account) => `<div class="account"><span>${esc(account.email)}</span><button type="button" data-action="delete-account" data-id="${account.id}">Quitar</button></div>`)
    .join("") || `<p class="help">Todavía no hay cuentas conectadas.</p>`;
  const client = data.clients.find((item) => item.id === state.configId) || null;
  const clientOptions = [`<option value="">Nuevo cliente</option>`]
    .concat(data.clients.map((item) => `<option value="${item.id}" ${item.id === state.configId ? "selected" : ""}>${esc(item.name)}</option>`))
    .join("");
  const accountOptions = [`<option value="">Sin cuenta</option>`]
    .concat(data.accounts.map((account) => `<option value="${account.id}" ${client && client.gmail_account_id === account.id ? "selected" : ""}>${esc(account.email)}</option>`))
    .join("");
  const recipients = (client?.recipients || [])
    .map((item) => `<div class="recipient"><span>${esc(item.name ? `${item.name} · ` : "")}${esc(item.email)}</span><button type="button" data-action="delete-recipient" data-id="${item.id}">Quitar</button></div>`)
    .join("") || `<p class="help">Sin destinatarios.</p>`;
  const keywords = (client?.keywords || [])
    .map((item) => `<div class="keyword"><span>${esc(item.phrase)} → ${esc(item.section_name)} · peso ${item.weight}</span><button type="button" data-action="delete-keyword" data-id="${item.id}">Quitar</button></div>`)
    .join("") || `<p class="help">Sin palabras clave. Una nota entra al cliente cuando el texto contiene la frase.</p>`;
  const library = data.libraries_ready
    ? ""
    : `<p class="warning">Faltan las librerías de Google. En la carpeta del proyecto ejecuta <code>python -m pip install -r requirements-sintesis.txt</code>.</p>`;
  root.innerHTML = `<div class="config-grid">
    <div class="panel stack">
      <h2>Cliente</h2>
      <label>Elegir <select id="configClient">${clientOptions}</select></label>
      <label>Nombre <input id="clientName" value="${esc(client?.name || "")}"></label>
      <label>Hora de envío <input id="sendTime" type="time" value="${esc(client?.send_time || "08:00")}"></label>
      <label>Asunto <input id="subjectTemplate" value="${esc(client?.subject_template || "Síntesis {cliente} — {fecha}")}"></label>
      <p class="help">Puedes usar {cliente}, {fecha} y {fecha_larga}.</p>
      <label class="row-actions"><input id="useBcc" type="checkbox" ${!client || client.use_bcc ? "checked" : ""}> Mandar a los destinatarios en copia oculta</label>
      <label>Cuenta de Gmail que envía <select id="gmailAccount">${accountOptions}</select></label>
      <div class="row-actions">
        <button class="primary" type="button" data-action="save-client">Guardar cliente</button>
        ${client ? `<button type="button" data-action="delete-client" data-id="${client.id}">Eliminar</button>` : ""}
      </div>
      ${client ? `<h3>Destinatarios</h3>${recipients}
        <div class="split"><input id="recipientEmail" placeholder="correo@cliente.com"><button type="button" data-action="add-recipient">Agregar</button></div>
        <h3>Palabras clave</h3>${keywords}
        <div class="split">
          <input id="keywordPhrase" placeholder="frase">
          <input id="keywordSection" placeholder="grupo">
        </div>
        <div class="row-actions">
          <label>Peso <input id="keywordWeight" type="number" min="1" max="10" value="1"></label>
          <button type="button" data-action="add-keyword">Agregar palabra</button>
        </div>` : `<p class="help">Guarda el cliente para agregar destinatarios y palabras clave.</p>`}
    </div>
    <aside class="panel stack">
      <h2>Gmail</h2>
      <p>Quien administra el correo entra una sola vez. El personal de la mesa no abre Gmail: al marcar la síntesis como revisada, el correo sale desde la cuenta conectada.</p>
      ${library}
      <p class="help">${data.credentials_loaded ? "El JSON de Google ya está cargado." : "Falta el JSON del cliente OAuth."}</p>
      <ol class="help">
        <li>En Google Cloud activa la API de Gmail.</li>
        <li>Configura la pantalla de consentimiento. En Workspace puede quedar en Interno.</li>
        <li>Crea un cliente OAuth de tipo Aplicación de escritorio.</li>
        <li>Si Google pide un redirect, usa <code>${esc(data.redirect_uri)}</code>.</li>
        <li>Sube el JSON y pulsa Conectar cuenta.</li>
      </ol>
      <label>Archivo de credenciales <input id="credentialsFile" type="file" accept="application/json,.json"></label>
      <div class="row-actions">
        <button type="button" id="uploadCredentials">Subir JSON</button>
        <button class="primary" type="button" data-action="connect-gmail" ${data.libraries_ready && data.credentials_loaded ? "" : "disabled"}>Conectar cuenta</button>
      </div>
      <h3>Cuentas conectadas</h3>
      ${accounts}
      <p class="help">Quitar la cuenta de esta mesa no revoca el permiso dentro de Google.</p>
    </aside>
  </div>`;
}

function cloneLayout() {
  const names = [...document.querySelectorAll("#sectionList .section")].map((section) =>
    section.querySelector(".section-name").value.trim()
  );
  return {
    sections: state.desk.sections.map((section, index) => ({
      name: names[index] || section.name,
      item_ids: section.items.map((item) => item.item_id),
    })),
    discarded_ids: state.desk.discarded.map((item) => item.item_id),
  };
}

function take(layout, itemId) {
  for (const section of layout.sections) {
    const index = section.item_ids.indexOf(itemId);
    if (index >= 0) {
      section.item_ids.splice(index, 1);
      return;
    }
  }
  const index = layout.discarded_ids.indexOf(itemId);
  if (index >= 0) layout.discarded_ids.splice(index, 1);
}

async function commitLayout(layout) {
  if (state.busy || !state.desk?.synthesis) return;
  state.busy = true;
  try {
    const data = await api(`/api/syntheses/${state.desk.synthesis.id}/layout`, {
      method: "POST",
      body: layout,
    });
    state.desk = data.desk;
    renderDesk();
    if (data.schedule_cancelled) toast(data.message);
  } catch (error) {
    toast(error.message);
    await loadDesk();
  } finally {
    state.busy = false;
  }
}

function moveWithin(itemId, direction) {
  const layout = cloneLayout();
  for (const section of layout.sections) {
    const index = section.item_ids.indexOf(itemId);
    const target = index + direction;
    if (index >= 0 && target >= 0 && target < section.item_ids.length) {
      const [id] = section.item_ids.splice(index, 1);
      section.item_ids.splice(target, 0, id);
      commitLayout(layout);
    }
  }
}

function moveToSection(itemId, sectionName) {
  if (!sectionName) return;
  const layout = cloneLayout();
  take(layout, itemId);
  const section = layout.sections.find((item) => item.name === sectionName);
  if (!section) return;
  section.item_ids.push(itemId);
  commitLayout(layout);
}

function discard(itemId) {
  const layout = cloneLayout();
  take(layout, itemId);
  layout.discarded_ids.push(itemId);
  commitLayout(layout);
}

function restore(itemId) {
  const item = state.desk.discarded.find((note) => note.item_id === itemId);
  const layout = cloneLayout();
  take(layout, itemId);
  const name = item?.section_name || layout.sections[0]?.name || "General";
  let section = layout.sections.find((entry) => entry.name === name);
  if (!section) {
    section = { name, item_ids: [] };
    layout.sections.push(section);
  }
  section.item_ids.push(itemId);
  commitLayout(layout);
}

function moveBefore(itemId, sectionIndex, beforeId) {
  if (beforeId === itemId) return;
  const layout = cloneLayout();
  take(layout, itemId);
  const ids = layout.sections[sectionIndex].item_ids;
  if (beforeId) {
    const index = ids.indexOf(beforeId);
    ids.splice(index < 0 ? ids.length : index, 0, itemId);
  } else ids.push(itemId);
  commitLayout(layout);
}

async function review() {
  const desk = state.desk;
  if (!desk?.synthesis) {
    await tell("Todavía no hay síntesis", "Primero tienen que entrar notas al cliente.");
    return;
  }
  if (!desk.readiness.ok) {
    const missing = desk.readiness.checks.filter((check) => !check.ok).map((check) => check.label);
    await tell("Falta algo para enviar", missing.join("\n"));
    return;
  }
  const recipients = desk.recipients.map((item) => item.email).join("\n");
  const accepted = await ask(
    "Marcar revisada",
    `${desk.plan_text}\n\nDestinatarios:\n${recipients}`,
    "Confirmar envío"
  );
  if (!accepted) return;
  try {
    const data = await api(`/api/syntheses/${desk.synthesis.id}/review`, { method: "POST", body: {} });
    state.desk = data.desk;
    renderDesk();
    toast(data.message);
    setStatus();
  } catch (error) {
    toast(error.message);
    await loadDesk();
  }
}

async function loadExample() {
  const data = await api("/api/notes/example", { method: "POST", body: { fecha: state.edition } });
  state.clientId = data.client_id;
  state.configId = data.client_id;
  state.edition = data.edition_date;
  remember();
  await loadBootstrap();
  toast(data.created ? "Día de ejemplo listo." : "El ejemplo de hoy ya estaba cargado.");
  switchTab("desk");
}

function notePayload() {
  return {
    fecha: $("noteDate").value,
    medio: $("noteMedium").value,
    fuente: $("noteOutlet").value,
    programa: $("noteProgram").value,
    hora: $("noteTime").value,
    titulo: $("noteTitle").value,
    texto: $("noteBody").value,
    autor: $("noteAuthor").value,
    url: $("noteUrl").value,
  };
}

function fillNoteForm(note) {
  state.editingId = note.note_id;
  $("noteDate").value = note.published_on;
  $("noteMedium").value = note.medium;
  $("noteOutlet").value = note.outlet;
  $("noteProgram").value = note.program;
  $("noteTime").value = note.published_time;
  $("noteTitle").value = note.title;
  $("noteBody").value = note.body;
  $("noteAuthor").value = note.author;
  $("noteUrl").value = note.url;
  $("noteFormTitle").textContent = "Editar nota";
  $("saveNote").textContent = "Guardar cambios";
  $("cancelEdit").hidden = false;
}

function clearNoteForm() {
  state.editingId = null;
  $("noteForm").reset();
  $("noteDate").value = state.edition;
  $("noteFormTitle").textContent = "Nueva nota";
  $("saveNote").textContent = "Agregar nota";
  $("cancelEdit").hidden = true;
}

async function saveNote(event) {
  event.preventDefault();
  const payload = notePayload();
  try {
    if (state.editingId) {
      await api(`/api/notes/${state.editingId}`, { method: "PUT", body: payload });
      toast("Nota actualizada.");
    } else {
      await api("/api/notes", { method: "POST", body: payload });
      toast("Nota agregada y clasificada.");
    }
    state.edition = payload.fecha;
    remember();
    clearNoteForm();
    await loadNotes();
    if (state.clientId) await loadDesk();
  } catch (error) {
    toast(error.message);
  }
}

async function saveClient() {
  const payload = {
    name: $("clientName").value,
    send_time: $("sendTime").value,
    subject_template: $("subjectTemplate").value,
    use_bcc: $("useBcc").checked,
    gmail_account_id: $("gmailAccount").value || null,
  };
  try {
    const saved = state.configId
      ? await api(`/api/clients/${state.configId}`, { method: "PUT", body: payload })
      : await api("/api/clients", { method: "POST", body: payload });
    state.configId = saved.id;
    state.clientId = saved.id;
    remember();
    await loadBootstrap();
    renderConfig();
    toast("Cliente guardado.");
  } catch (error) {
    toast(error.message);
  }
}

document.querySelector(".tabs").addEventListener("click", (event) => {
  const button = event.target.closest("[data-tab]");
  if (button) switchTab(button.dataset.tab);
});

$("view-desk").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button || state.busy) return;
  try {
  const action = button.dataset.action;
  const itemId = Number(button.dataset.itemId || 0);
  const index = Number(button.dataset.index || 0);
  if (action === "example") {
    await loadExample();
    return;
  }
  if (action === "go-config") return switchTab("config");
  if (action === "up") return moveWithin(itemId, -1);
  if (action === "down") return moveWithin(itemId, 1);
  if (action === "discard") return discard(itemId);
  if (action === "restore") return restore(itemId);
  if (action === "review") return review();
  if (action === "reclassify") {
    await api("/api/desk/reclassify", { method: "POST", body: { client_id: state.clientId, date: state.edition } });
    toast("Notas automáticas reclasificadas.");
    return loadDesk();
  }
  if (action === "add-section") {
    const layout = cloneLayout();
    let name = "Nueva sección";
    let counter = 2;
    const names = new Set(layout.sections.map((section) => section.name.toLocaleLowerCase("es")));
    while (names.has(name.toLocaleLowerCase("es"))) name = `Nueva sección ${counter++}`;
    layout.sections.push({ name, item_ids: [] });
    return commitLayout(layout);
  }
  if (action === "section-up" || action === "section-down") {
    const layout = cloneLayout();
    const target = index + (action === "section-up" ? -1 : 1);
    if (target < 0 || target >= layout.sections.length) return;
    const [section] = layout.sections.splice(index, 1);
    layout.sections.splice(target, 0, section);
    return commitLayout(layout);
  }
  if (action === "section-delete") {
    const layout = cloneLayout();
    if (layout.sections[index].item_ids.length) return;
    layout.sections.splice(index, 1);
    return commitLayout(layout);
  }
  if (action === "attach") {
    const select = document.querySelector(`.attach-section[data-note-id="${button.dataset.noteId}"]`);
    state.desk = await api("/api/desk/attach", {
      method: "POST",
      body: {
        client_id: state.clientId,
        date: state.edition,
        note_id: Number(button.dataset.noteId),
        section_name: select ? select.value : "General",
      },
    });
    renderDesk();
    return;
  }
  if (action === "reopen") {
    state.desk = await api(`/api/syntheses/${state.desk.synthesis.id}/reopen`, { method: "POST", body: {} });
    renderDesk();
    toast("La síntesis quedó abierta para corrección.");
    return;
  }
  if (action === "retry") {
    const data = await api(`/api/syntheses/${state.desk.synthesis.id}/retry`, { method: "POST", body: {} });
    state.desk = data.desk;
    renderDesk();
    toast(data.message);
  }
  } catch (error) {
    toast(error.message);
    await loadDesk().catch(() => {});
  }
});

$("view-desk").addEventListener("change", (event) => {
  const target = event.target;
  if (target.id === "clientSelect") {
    state.clientId = Number(target.value);
    state.configId = state.clientId;
    remember();
    loadDesk();
  }
  if (target.id === "editionDate") {
    state.edition = target.value;
    remember();
    $("noteDate").value = state.edition;
    loadDesk();
  }
  if (target.classList.contains("section-name")) commitLayout(cloneLayout());
  if (target.classList.contains("move-section")) {
    moveToSection(Number(target.dataset.itemId), target.value);
  }
});

$("view-desk").addEventListener("dragstart", (event) => {
  const card = event.target.closest(".note");
  if (!card) return;
  state.dragId = Number(card.dataset.itemId);
  event.dataTransfer.setData("text/plain", String(state.dragId));
  event.dataTransfer.effectAllowed = "move";
});

$("view-desk").addEventListener("dragover", (event) => {
  if (!state.dragId) return;
  if (event.target.closest(".note, .section, .discard-bin")) event.preventDefault();
});

$("view-desk").addEventListener("drop", (event) => {
  if (!state.dragId) return;
  event.preventDefault();
  const itemId = state.dragId;
  state.dragId = null;
  if (event.target.closest(".discard-bin")) {
    discard(itemId);
    return;
  }
  const section = event.target.closest(".section");
  if (!section) return;
  const card = event.target.closest(".note");
  moveBefore(itemId, Number(section.dataset.index), card ? Number(card.dataset.itemId) : null);
});

$("noteForm").addEventListener("submit", saveNote);
$("cancelEdit").addEventListener("click", clearNoteForm);
$("reloadNotes").addEventListener("click", loadNotes);
$("loadExample").addEventListener("click", loadExample);
$("noteDate").addEventListener("change", () => {
  state.edition = $("noteDate").value;
  remember();
  loadNotes();
});
$("importNotes").addEventListener("click", async () => {
  try {
    const parsed = JSON.parse($("importJson").value || "[]");
    const notes = Array.isArray(parsed) ? parsed : parsed.notes;
    const result = await api("/api/notes/import", { method: "POST", body: { notes } });
    $("importJson").value = "";
    toast(`${result.created} notas importadas.`);
    await loadNotes();
  } catch (error) {
    toast(error.message);
  }
});

$("view-notes").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const note = state.notes.find((item) => item.note_id === Number(button.dataset.noteId));
  if (button.dataset.action === "edit-note" && note) fillNoteForm(note);
  if (button.dataset.action === "delete-note") {
    const accepted = await ask("Borrar nota", "Se quita de las síntesis que todavía no se envían.", "Borrar");
    if (!accepted) return;
    try {
      await api(`/api/notes/${button.dataset.noteId}`, { method: "DELETE" });
      await loadNotes();
      toast("Nota borrada.");
    } catch (error) {
      toast(error.message);
    }
  }
});

$("view-sends").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  if (button.dataset.action === "open-send") {
    const clientId = Number(button.dataset.clientId);
    if (clientId) state.clientId = clientId;
    state.edition = button.dataset.date;
    remember();
    switchTab("desk");
  }
  if (button.dataset.action === "retry-send") {
    try {
      const data = await api(`/api/syntheses/${button.dataset.synthesisId}/retry`, { method: "POST", body: {} });
      toast(data.message);
      await loadSends();
    } catch (error) {
      toast(error.message);
      await loadSends();
    }
  }
});

$("view-config").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (event.target.id === "uploadCredentials") {
    const file = $("credentialsFile").files[0];
    if (!file) {
      toast("Elige el JSON descargado de Google Cloud.");
      return;
    }
    try {
      const parsed = JSON.parse(await file.text());
      await api("/api/gmail/credentials", { method: "POST", body: parsed });
      await loadBootstrap();
      renderConfig();
      toast("Credenciales guardadas. Ahora conecta la cuenta.");
    } catch (error) {
      toast(error.message);
    }
    return;
  }
  if (!button) return;
  const action = button.dataset.action;
  if (action === "save-client") return saveClient();
  if (action === "connect-gmail") {
    location.href = "/api/gmail/connect";
    return;
  }
  if (action === "add-recipient") {
    try {
      await api(`/api/clients/${state.configId}/recipients`, {
        method: "POST",
        body: { email: $("recipientEmail").value },
      });
      await loadBootstrap();
      renderConfig();
    } catch (error) {
      toast(error.message);
    }
  }
  if (action === "add-keyword") {
    try {
      await api("/api/keywords", {
        method: "POST",
        body: {
          client_id: state.configId,
          phrase: $("keywordPhrase").value,
          section_name: $("keywordSection").value,
          weight: Number($("keywordWeight").value || 1),
        },
      });
      await loadBootstrap();
      renderConfig();
    } catch (error) {
      toast(error.message);
    }
  }
  if (action === "delete-recipient" || action === "delete-keyword" || action === "delete-account") {
    const path = {
      "delete-recipient": `/api/recipients/${button.dataset.id}`,
      "delete-keyword": `/api/keywords/${button.dataset.id}`,
      "delete-account": `/api/gmail/accounts/${button.dataset.id}`,
    }[action];
    await api(path, { method: "DELETE" });
    await loadBootstrap();
    renderConfig();
  }
  if (action === "delete-client") {
    const accepted = await ask("Eliminar cliente", "Se borran sus palabras, destinatarios y síntesis no enviadas.", "Eliminar");
    if (!accepted) return;
    try {
      await api(`/api/clients/${button.dataset.id}`, { method: "DELETE" });
      state.configId = null;
      await loadBootstrap();
      state.clientId = state.bootstrap.clients[0]?.id || null;
      renderConfig();
      toast("Cliente eliminado.");
    } catch (error) {
      toast(error.message);
    }
  }
});

$("view-config").addEventListener("change", (event) => {
  if (event.target.id === "configClient") {
    state.configId = Number(event.target.value) || null;
    renderConfig();
  }
});

setInterval(() => {
  if (state.tab !== "desk" || state.busy || !state.clientId || !$("modal").hidden) return;
  const active = document.activeElement;
  if (active && active.closest && active.closest("input, textarea, select")) return;
  loadDesk().catch(() => {});
}, 30000);

boot().catch((error) => {
  $("statusLine").textContent = error.message;
});
