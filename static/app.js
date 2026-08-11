const form = document.querySelector("#uploadForm");
const input = document.querySelector("#pdfs");
const dropzone = document.querySelector("#dropzone");
const fileStrip = document.querySelector("#fileStrip");
const results = document.querySelector("#results");
const statusNode = document.querySelector("#status");
const extractButton = document.querySelector("#extractButton");
const fileTemplate = document.querySelector("#fileTemplate");
const resultTemplate = document.querySelector("#resultTemplate");

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function selectedFiles() {
  return Array.from(input.files || []);
}

function renderFiles() {
  fileStrip.replaceChildren();
  const files = selectedFiles();
  extractButton.disabled = files.length === 0;
  statusNode.textContent = files.length ? `${files.length} PDF${files.length === 1 ? "" : "s"}` : "Listo";

  for (const file of files) {
    const chip = fileTemplate.content.firstElementChild.cloneNode(true);
    chip.querySelector(".file-name").textContent = file.name;
    chip.querySelector(".file-size").textContent = formatBytes(file.size);
    fileStrip.append(chip);
  }
}

function renderError(message) {
  const node = document.createElement("div");
  node.className = "error";
  node.textContent = message;
  results.prepend(node);
}

function basename(path) {
  return path.split(/[\\/]/).pop();
}

async function loadGenres() {
  const select = document.querySelector("#genre");
  if (!select) return;
  try {
    const response = await fetch("/genres");
    if (!response.ok) return;
    const payload = await response.json();
    const current = select.value || payload.default || "nota_informativa";
    select.replaceChildren();
    for (const genre of payload.genres || []) {
      const option = document.createElement("option");
      option.value = genre.id;
      option.textContent = genre.label;
      if (genre.description) option.title = genre.description;
      if (genre.id === current) option.selected = true;
      select.append(option);
    }
  } catch {
    // Mantiene las opciones estaticas del HTML.
  }
}

function renderResult(result) {
  const card = resultTemplate.content.firstElementChild.cloneNode(true);
  const name = basename(result.source_pdf);
  card.querySelector("h2").textContent = name;
  card.querySelector(".meta").textContent =
    `${result.page_count} paginas - ${result.word_count} palabras - ${result.char_count} caracteres` +
    (result.genre ? ` - ${result.genre}` : "") +
    (result.needs_ocr ? " - necesita OCR" : "");
  card.querySelector(".txt-link").href = result.output_txt_url;

  const jsonLink = card.querySelector(".json-link");
  if (result.output_json_url) {
    jsonLink.href = result.output_json_url;
  } else {
    jsonLink.remove();
  }

  card.querySelector("pre").textContent = result.preview || "Sin texto extraido.";
  results.prepend(card);
}

loadGenres();
input.addEventListener("change", renderFiles);

for (const eventName of ["dragenter", "dragover"]) {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("is-over");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("is-over");
  });
}

dropzone.addEventListener("drop", (event) => {
  const dataTransfer = new DataTransfer();
  for (const file of event.dataTransfer.files) {
    if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
      dataTransfer.items.add(file);
    }
  }
  input.files = dataTransfer.files;
  renderFiles();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const files = selectedFiles();
  if (!files.length) return;

  const formData = new FormData();
  for (const file of files) {
    formData.append("pdfs", file);
  }
  formData.append("mode", new FormData(form).get("mode") || "human");
  formData.append("genre", document.querySelector("#genre").value || "nota_informativa");
  formData.append("pagesJson", document.querySelector("#pagesJson").checked ? "true" : "false");
  formData.append("headerPercent", document.querySelector("#headerPercent").value || "8");
  formData.append("footerPercent", document.querySelector("#footerPercent").value || "5");

  extractButton.disabled = true;
  statusNode.textContent = "Extrayendo";

  try {
    const response = await fetch("/extract", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "No se pudo extraer el texto.");
    }

    for (const error of payload.errors || []) {
      renderError(`${error.file}: ${error.error}`);
    }
    for (const result of payload.results || []) {
      renderResult(result);
    }
    statusNode.textContent = `${(payload.results || []).length} procesado${(payload.results || []).length === 1 ? "" : "s"}`;
  } catch (error) {
    renderError(error.message);
    statusNode.textContent = "Error";
  } finally {
    extractButton.disabled = selectedFiles().length === 0;
  }
});
