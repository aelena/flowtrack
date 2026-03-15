const $ = (sel) => document.querySelector(sel);

const apiUrlInput = $("#apiUrl");
const apiKeyInput = $("#apiKey");
const projectSelect = $("#project");
const snippetArea = $("#snippet");
const saveUrlBtn = $("#saveUrl");
const saveSnippetBtn = $("#saveSnippet");
const refreshBtn = $("#refreshProjects");
const statusEl = $("#status");

// ── Helpers ──────────────────────────────────────────────

function showStatus(message, type = "success") {
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
  statusEl.hidden = false;
  setTimeout(() => {
    statusEl.hidden = true;
  }, 3000);
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
    throw new Error("Set API URL and API Key first");
  }

  const opts = {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${apiUrl}${path}`, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

// ── Projects ─────────────────────────────────────────────

async function loadProjects() {
  try {
    const projects = await apiRequest("GET", "/api/extension/projects");
    projectSelect.innerHTML = '<option value="">-- Select project --</option>';
    projects.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.name;
      projectSelect.appendChild(opt);
    });
  } catch (err) {
    showStatus(err.message, "error");
  }
}

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
apiKeyInput.addEventListener("change", saveSettings);
refreshBtn.addEventListener("click", loadProjects);

// ── Save URL ─────────────────────────────────────────────

saveUrlBtn.addEventListener("click", async () => {
  const projectId = projectSelect.value;
  if (!projectId) {
    showStatus("Select a project first", "error");
    return;
  }

  saveUrlBtn.disabled = true;
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    await apiRequest("POST", "/api/extension/snippet", {
      project_id: projectId,
      type: "url",
      content: tab.url,
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
  const projectId = projectSelect.value;
  if (!projectId) {
    showStatus("Select a project first", "error");
    return;
  }

  let text = snippetArea.value.trim();

  // If textarea is empty, try to get selected text from the active tab
  if (!text) {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      const [result] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => window.getSelection().toString(),
      });
      text = result?.result?.trim() || "";
    } catch {
      // scripting may not be available on all pages
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

chrome.storage.local.get(["apiUrl", "apiKey"], (data) => {
  if (data.apiUrl) apiUrlInput.value = data.apiUrl;
  if (data.apiKey) apiKeyInput.value = data.apiKey;
  if (data.apiUrl && data.apiKey) loadProjects();
});
