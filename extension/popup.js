const $ = (sel) => document.querySelector(sel);

const apiUrlInput = $("#apiUrl");
const apiKeyInput = $("#apiKey");
const projectSelect = $("#project");
const snippetArea = $("#snippet");
const saveUrlBtn = $("#saveUrl");
const saveSnippetBtn = $("#saveSnippet");
const refreshBtn = $("#refreshProjects");
const newProjectBtn = $("#newProject");
const newProjectRow = $("#newProjectRow");
const newProjectName = $("#newProjectName");
const createProjectBtn = $("#createProject");
const cancelNewProjectBtn = $("#cancelNewProject");
const statusEl = $("#status");

// ── Helpers ──────────────────────────────────────────────

let statusTimer;

function showStatus(message, type = "success") {
  clearTimeout(statusTimer);
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
  statusEl.hidden = false;
  // Errors stay put. Auto-hiding them after three seconds is how a real cause
  // ("API key rejected") gets replaced by a symptom ("select a project first").
  if (type !== "error") {
    statusTimer = setTimeout(() => {
      statusEl.hidden = true;
    }, 3000);
  }
}

function getSettings() {
  return {
    apiUrl: apiUrlInput.value.replace(/\/+$/, ""),
    apiKey: apiKeyInput.value,
  };
}

async function apiRequest(method, path, body = null) {
  const { apiUrl, apiKey } = getSettings();
  if (!apiUrl || !apiKey) {
    throw new Error("Set both the API URL and the API key above");
  }

  const opts = {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
  };
  if (body) opts.body = JSON.stringify(body);

  let res;
  try {
    res = await fetch(`${apiUrl}${path}`, opts);
  } catch {
    // fetch rejects without a status for the whole class of "never got there":
    // FlowTrack not running, wrong port, or the origin blocked. Say which
    // things to check rather than surfacing a bare "Failed to fetch".
    throw new Error(`Cannot reach ${apiUrl} — is docker compose up, and is the URL right?`);
  }

  if (res.status === 401) {
    throw new Error("API key rejected. It must match API_KEY in FlowTrack's .env");
  }
  if (res.status === 422 && path === "/api/extension/projects") {
    throw new Error("The API key header was missing");
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

// ── Projects ─────────────────────────────────────────────

// Chosen in the picker to mean "no project yet". The server resolves it to the
// Inbox project and creates that on first use, so an idea can be captured
// before it has a home.
const INBOX = "__inbox__";

async function loadProjects() {
  try {
    const projects = await apiRequest("GET", "/api/extension/projects");
    projectSelect.innerHTML =
      `<option value="${INBOX}">Inbox (unfiled)</option>` +
      '<option value="" disabled>──────────</option>';
    projects.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.name;
      projectSelect.appendChild(opt);
    });

    // Re-select the remembered project, but only if it is still in the list.
    const { defaultProjectId } = await chrome.storage.local.get(["defaultProjectId"]);
    if (defaultProjectId === INBOX) {
      projectSelect.value = INBOX;
    } else if (defaultProjectId && projects.some((p) => p.id === defaultProjectId)) {
      projectSelect.value = defaultProjectId;
    } else {
      // Either nothing was remembered, or it was archived or deleted. Fall back
      // to the Inbox rather than blocking the clip on picking a project.
      if (defaultProjectId) {
        await chrome.storage.local.remove(["defaultProjectId", "defaultProjectName"]);
      }
      projectSelect.value = INBOX;
    }
  } catch (err) {
    // Leave the picker visibly unloaded rather than half-populated.
    projectSelect.innerHTML = '<option value="">Not loaded</option>';
    showStatus(err.message, "error");
  }
}

// ── Creating a project from the clipper ──────────────────

function toggleNewProject(show) {
  newProjectRow.hidden = !show;
  if (show) {
    newProjectName.value = "";
    newProjectName.focus();
  }
}

newProjectBtn.addEventListener("click", () => toggleNewProject(newProjectRow.hidden));
cancelNewProjectBtn.addEventListener("click", () => toggleNewProject(false));
newProjectName.addEventListener("keydown", (e) => {
  if (e.key === "Enter") createProjectBtn.click();
  if (e.key === "Escape") toggleNewProject(false);
});

createProjectBtn.addEventListener("click", async () => {
  const name = newProjectName.value.trim();
  if (!name) {
    showStatus("Give the project a name", "error");
    return;
  }

  createProjectBtn.disabled = true;
  try {
    const created = await apiRequest("POST", "/api/extension/project", { name });
    await loadProjects();
    // Select it and remember it, so the clip about to be saved — and the next
    // right-click — go to the project that was just made for them.
    projectSelect.value = created.id;
    await chrome.storage.local.set({
      defaultProjectId: created.id,
      defaultProjectName: created.name,
    });
    toggleNewProject(false);
    showStatus(`Created "${created.name}"`);
  } catch (err) {
    showStatus(err.message, "error");
  } finally {
    createProjectBtn.disabled = false;
  }
});

// ── Save settings on change ──────────────────────────────

function saveSettings() {
  chrome.storage.local.set({
    apiUrl: apiUrlInput.value,
    apiKey: apiKeyInput.value,
  });
}

apiUrlInput.addEventListener("change", () => {
  saveSettings();
  loadProjects();
});
// This used to only save. Typing the URL first fired a load with an empty key,
// that error auto-hid, and filling the key in afterwards never repopulated the
// dropdown — so the picker sat empty and the only clue was gone.
apiKeyInput.addEventListener("change", () => {
  saveSettings();
  loadProjects();
});
refreshBtn.addEventListener("click", loadProjects);

// The picked project is what the right-click menu clips to, so it has to
// outlive the popup.
projectSelect.addEventListener("change", () => {
  const id = projectSelect.value;
  if (!id) return; // the separator row
  chrome.storage.local.set({
    defaultProjectId: id,
    defaultProjectName: projectSelect.selectedOptions[0]?.textContent || "",
  });
});

// null tells the API to file the clip in the Inbox.
function chosenProjectId() {
  const value = projectSelect.value;
  return value === INBOX ? null : value;
}

// ── Save URL ─────────────────────────────────────────────

saveUrlBtn.addEventListener("click", async () => {
  if (!projectSelect.value) {
    showStatus("Select a project or Inbox first", "error");
    return;
  }
  const projectId = chosenProjectId();

  saveUrlBtn.disabled = true;
  try {
    const tab = await activeTab();
    await apiRequest("POST", "/api/extension/snippet", {
      project_id: projectId,
      type: "url",
      content: tab.url,
      source_url: tab.url,
    });
    showStatus("URL saved");
  } catch (err) {
    showStatus(err.message, "error");
  } finally {
    saveUrlBtn.disabled = false;
  }
});

// ── Save Snippet ─────────────────────────────────────────

saveSnippetBtn.addEventListener("click", async () => {
  if (!projectSelect.value) {
    showStatus("Select a project or Inbox first", "error");
    return;
  }
  const projectId = chosenProjectId();

  let text = snippetArea.value.trim();
  const tab = await activeTab();

  // If textarea is empty, try to get selected text from the active tab
  if (!text) {
    try {
      const [result] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => window.getSelection().toString(),
      });
      text = result?.result?.trim() || "";
    } catch (err) {
      // chrome:// pages, the web store and PDFs cannot be scripted. Say so
      // instead of reporting "select some text first" when text was selected.
      console.warn("FlowTrack Clipper: cannot read the selection here:", err.message);
      showStatus("Cannot read the selection on this page — paste it instead", "error");
      return;
    }
  }

  if (!text) {
    showStatus("Enter or select some text first", "error");
    return;
  }

  saveSnippetBtn.disabled = true;
  try {
    await apiRequest("POST", "/api/extension/snippet", {
      project_id: projectId,
      type: "snippet",
      content: text,
      source_url: tab?.url || null,
    });
    snippetArea.value = "";
    showStatus("Snippet saved");
  } catch (err) {
    showStatus(err.message, "error");
  } finally {
    saveSnippetBtn.disabled = false;
  }
});

// ── Init ─────────────────────────────────────────────────

const DEFAULT_API_URL = "http://localhost:7028";

chrome.storage.local.get(["apiUrl", "apiKey"], (data) => {
  // Filled as a real value, not left to the placeholder. An empty field showing
  // grey example text is indistinguishable from a configured one, and the popup
  // then silently does nothing: the project load is gated on both fields, so
  // there is no request and therefore no error to read.
  // The key goes in first: saveSettings() writes both fields, so saving the
  // defaulted URL before restoring the key would blank a stored key.
  if (data.apiKey) apiKeyInput.value = data.apiKey;

  apiUrlInput.value = data.apiUrl || DEFAULT_API_URL;
  if (!data.apiUrl) saveSettings();

  if (apiUrlInput.value && apiKeyInput.value) {
    loadProjects();
  } else {
    showStatus("Paste the API key from FlowTrack's .env to load your projects", "error");
  }
});
