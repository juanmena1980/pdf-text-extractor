const statusLine = document.querySelector("#status");
const excelInput = document.querySelector("#excel");
const dropzone = document.querySelector("#dropzone");
const fileName = document.querySelector("#fileName");
const mapping = document.querySelector("#mapping");
const sheetSelect = document.querySelector("#sheet");
const linkSelect = document.querySelector("#linkColumn");
const textSelect = document.querySelector("#textColumn");
const genreSelect = document.querySelector("#genre");
const headerPercent = document.querySelector("#headerPercent");
const footerPercent = document.querySelector("#footerPercent");
const sheetMeta = document.querySelector("#sheetMeta");
const sampleTable = document.querySelector("#sampleTable");
const formError = document.querySelector("#formError");
const startButton = document.querySelector("#startButton");
const downloadLink = document.querySelector("#download");
const progressPanel = document.querySelector("#progressPanel");
const progressMessage = document.querySelector("#progressMessage");
const progressBar = document.querySelector("#progressBar");
const summary = document.querySelector("#summary");
const results = document.querySelector("#results");
const resultBody = document.querySelector("#resultBody");
const detail = document.querySelector("#detail");
const form = document.querySelector("#uploadForm");

let preview = null;
let excelFile = null;
let selectedRow = null;
let pollTimer = null;

function setStatus(text) {
  statusLine.textContent = text;
}

function showError(message) {
  formError.hidden = !message;
  formError.textContent = message || "";
}

function formatPercent(value) {
  if (value == null) return "—";
  return `${Number(value).toLocaleString("es-MX", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} %`;
}

function tone(value) {
  if (value == null) return "muted";
  if (value >= 99.95) return "good";
  if (value >= 90) return "ok";
  if (value >= 70) return "warn";
  return "bad";
}

function selectedSheet() {
  if (!preview) return null;
  return preview.sheets.find((sheet) => sheet.name === sheetSelect.value) || preview.sheets[0];
}

function fillSelect(select, options, preferred) {
  select.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Elige una columna";
  select.append(placeholder);
  options.forEach((option) => {
    const node = document.createElement("option");
    node.value = option;
    node.textContent = option;
    select.append(node);
  });
  select.value = options.includes(preferred) ? preferred : "";
}

function renderSample(sheet) {
  sampleTable.replaceChildren();
  if (!sheet.headers.length) {
    return;
  }
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  sheet.headers.forEach((header) => {
    const cell = document.createElement("th");
    cell.textContent = header;
    headRow.append(cell);
  });
  head.append(headRow);
  const body = document.createElement("tbody");
  sheet.sample.forEach((row) => {
    const tr = document.createElement("tr");
    sheet.headers.forEach((header) => {
      const cell = document.createElement("td");
      cell.textContent = row[header] || "";
      tr.append(cell);
    });
    body.append(tr);
  });
  sampleTable.append(head, body);
}

function renderMapping() {
  mapping.hidden = false;
  sheetSelect.replaceChildren();
  preview.sheets.forEach((sheet) => {
    const option = document.createElement("option");
    option.value = sheet.name;
    option.textContent = `${sheet.name} (${sheet.data_rows} filas)`;
    sheetSelect.append(option);
  });
  const suggested = preview.sheets.find((sheet) => sheet.suggested) || preview.sheets[0];
  sheetSelect.value = suggested.name;
  renderSheet();
}

function renderSheet() {
  const sheet = selectedSheet();
  if (!sheet) return;
  fillSelect(linkSelect, sheet.headers, sheet.suggested_link);
  fillSelect(textSelect, sheet.headers, sheet.suggested_text);
  const headerNote = sheet.header_row > 1 ? ` Encabezados en la fila ${sheet.header_row}.` : "";
  sheetMeta.textContent = `${sheet.data_rows} filas con datos.${headerNote}`;
  renderSample(sheet);
  startButton.disabled = false;
}

async function loadGenres() {
  const response = await fetch("/api/genres");
  const payload = await response.json();
  genreSelect.replaceChildren();
  payload.genres.forEach((genre) => {
    const option = document.createElement("option");
    option.value = genre.id;
    option.textContent = genre.label;
    option.title = genre.description || "";
    genreSelect.append(option);
  });
  genreSelect.value = payload.default || "nota_informativa";
}

async function loadPreview(file) {
  excelFile = file;
  fileName.textContent = file.name;
  showError("");
  setStatus("Leyendo Excel");
  const body = new FormData();
  body.append("excel", file);
  const response = await fetch("/api/preview", { method: "POST", body });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "No se pudo leer el Excel.");
  }
  preview = payload;
  renderMapping();
  setStatus("Listo para comparar");
}

function clearJobView() {
  progressPanel.hidden = true;
  summary.hidden = true;
  results.hidden = true;
  downloadLink.hidden = true;
  resultBody.replaceChildren();
  detail.replaceChildren();
  selectedRow = null;
}

function renderSummary(snapshot) {
  const data = snapshot.summary;
  summary.hidden = !data;
  if (!data) return;
  const cards = [
    ["Igualdad promedio", data.average == null ? "—" : formatPercent(data.average)],
    ["Igualdad mínima", data.minimum == null ? "—" : formatPercent(data.minimum)],
    ["Filas comparadas", `${data.compared} de ${data.rows}`],
    ["Sin capa de texto", String(data.needs_ocr)],
  ];
  summary.replaceChildren();
  cards.forEach(([label, value]) => {
    const card = document.createElement("article");
    const name = document.createElement("span");
    name.textContent = label;
    const strong = document.createElement("strong");
    strong.textContent = value;
    card.append(name, strong);
    summary.append(card);
  });
}

function rowState(row) {
  if (row.error) return row.error;
  if (row.needs_ocr) return "Sin capa de texto";
  return "Texto recuperado";
}

function renderDetail(row) {
  detail.replaceChildren();
  if (!row) {
    const empty = document.createElement("p");
    empty.textContent = "Selecciona una fila para leer las dos transcripciones.";
    detail.append(empty);
    return;
  }

  const title = document.createElement("h2");
  title.textContent = `Fila ${row.row}`;
  const score = document.createElement("p");
  score.className = `percent ${tone(row.equality)}`;
  score.textContent = formatPercent(row.equality);
  const meta = document.createElement("p");
  meta.className = "meta";
  const pages = row.pages || 0;
  meta.textContent = `${row.words_extracted} palabras extraídas · ${row.words_reviewed} revisadas · ${pages} ${pages === 1 ? "página" : "páginas"}`;
  detail.append(title, score, meta);

  if (row.needs_ocr) {
    const warning = document.createElement("p");
    warning.className = "warning";
    warning.textContent = "Este PDF no tiene capa de texto. La transcripción recuperada no está completa.";
    detail.append(warning);
  }
  if (row.error) {
    const warning = document.createElement("p");
    warning.className = "warning";
    warning.textContent = row.error;
    detail.append(warning);
  }

  const link = document.createElement("p");
  link.className = "link meta";
  if (/^https?:\/\//i.test(row.link || "")) {
    const anchor = document.createElement("a");
    anchor.href = row.link;
    anchor.target = "_blank";
    anchor.rel = "noopener";
    anchor.textContent = row.link;
    link.append(anchor);
  } else {
    link.textContent = row.link || "Sin liga";
  }
  detail.append(link);

  const columns = document.createElement("div");
  columns.className = "transcripts";
  [
    ["Texto extraído", row.extracted || ""],
    ["Transcripción revisada", row.reviewed || ""],
  ].forEach(([label, text]) => {
    const section = document.createElement("section");
    const heading = document.createElement("h3");
    heading.textContent = label;
    const block = document.createElement("div");
    block.className = "transcript";
    block.textContent = text || "(vacío)";
    section.append(heading, block);
    columns.append(section);
  });
  detail.append(columns);
}

function renderResults(snapshot) {
  const rows = snapshot.results || [];
  results.hidden = rows.length === 0;
  if (!rows.length) {
    detail.replaceChildren();
    return;
  }
  if (!rows.some((row) => row.row === selectedRow)) {
    selectedRow = rows[0].row;
  }
  resultBody.replaceChildren();
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    if (row.row === selectedRow) tr.className = "selected";
    tr.tabIndex = 0;
    tr.setAttribute("role", "button");
    tr.setAttribute("aria-label", `Fila ${row.row}, ${formatPercent(row.equality)}`);
    const values = [
      String(row.row),
      formatPercent(row.equality),
      `${row.words_extracted} / ${row.words_reviewed}`,
      String(row.pages || 0),
      rowState(row),
    ];
    values.forEach((value, index) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      if (index === 1) cell.className = `percent ${tone(row.equality)}`;
      tr.append(cell);
    });
    const select = () => {
      selectedRow = row.row;
      renderResults(snapshot);
    };
    tr.addEventListener("click", select);
    tr.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        select();
      }
    });
    resultBody.append(tr);
  });
  renderDetail(rows.find((row) => row.row === selectedRow));
}

function renderJob(snapshot) {
  const running = snapshot.status === "running";
  progressPanel.hidden = false;
  progressBar.max = snapshot.total || 1;
  progressBar.value = snapshot.done || 0;
  progressMessage.textContent = snapshot.message || (running ? "Procesando" : "Listo");
  setStatus(running ? `${snapshot.done} de ${snapshot.total}` : snapshot.status === "error" ? "Error" : "Listo");
  if (snapshot.error) showError(snapshot.error);
  renderSummary(snapshot);
  renderResults(snapshot);
  if (snapshot.download) {
    downloadLink.hidden = false;
    downloadLink.href = snapshot.download;
    downloadLink.textContent = "Descargar Excel de entrenamiento";
  }
  startButton.disabled = running;
}

async function poll(jobId) {
  window.clearTimeout(pollTimer);
  const response = await fetch(`/api/jobs/${jobId}`);
  const snapshot = await response.json();
  if (!response.ok) {
    throw new Error(snapshot.error || "No se pudo consultar el comparativo.");
  }
  renderJob(snapshot);
  if (snapshot.status === "running") {
    pollTimer = window.setTimeout(() => {
      poll(jobId).catch((error) => {
        showError(error.message);
        startButton.disabled = false;
      });
    }, 700);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  if (!excelFile) {
    showError("Primero elige el Excel.");
    return;
  }
  if (!linkSelect.value || !textSelect.value) {
    showError("Elige la columna de la liga y la de la transcripción.");
    return;
  }
  if (linkSelect.value === textSelect.value) {
    showError("La liga y la transcripción tienen que ser columnas distintas.");
    return;
  }
  startButton.disabled = true;
  clearJobView();
  progressPanel.hidden = false;
  progressMessage.textContent = "Iniciando";
  try {
    const body = new FormData();
    body.append("excel", excelFile);
    body.append("sheet", sheetSelect.value);
    body.append("link_column", linkSelect.value);
    body.append("text_column", textSelect.value);
    body.append("genre", genreSelect.value);
    body.append("header_percent", headerPercent.value);
    body.append("footer_percent", footerPercent.value);
    const response = await fetch("/api/jobs", { method: "POST", body });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "No se pudo iniciar el comparativo.");
    const url = new URL(window.location.href);
    url.searchParams.set("job", payload.id);
    window.history.replaceState(null, "", url);
    await poll(payload.id);
  } catch (error) {
    showError(error.message);
    setStatus("Error");
    startButton.disabled = false;
  }
});

excelInput.addEventListener("change", () => {
  const file = excelInput.files && excelInput.files[0];
  if (!file) return;
  loadPreview(file).catch((error) => {
    showError(error.message);
    setStatus("Error");
  });
});

sheetSelect.addEventListener("change", renderSheet);

["dragenter", "dragover"].forEach((name) => {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach((name) => {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragover");
  });
});

dropzone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files && event.dataTransfer.files[0];
  if (!file) return;
  loadPreview(file).catch((error) => {
    showError(error.message);
    setStatus("Error");
  });
});

loadGenres().catch(() => {
  showError("No se pudieron cargar los géneros del extractor.");
});

const initialJob = new URLSearchParams(window.location.search).get("job");
if (initialJob) {
  poll(initialJob).catch((error) => {
    showError(error.message);
    startButton.disabled = false;
  });
}
