// ── Context menu setup ───────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save-to-flowtrack",
    title: "Save to FlowTrack",
    contexts: ["selection"],
  });
});

// ── Context menu handler ─────────────────────────────────

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "save-to-flowtrack") return;

  const selectedText = info.selectionText;
  if (!selectedText) return;

  const data = await chrome.storage.local.get(["apiUrl", "apiKey"]);
  const apiUrl = data.apiUrl?.replace(/\/+$/, "");
  const apiKey = data.apiKey;

  if (!apiUrl || !apiKey) {
    // No settings configured — open the popup so the user can configure
    chrome.action.openPopup();
    return;
  }

  try {
    // Fetch projects to use the first one as default
    const projectsRes = await fetch(`${apiUrl}/api/extension/projects`, {
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
    });

    if (!projectsRes.ok) {
      throw new Error(`Failed to fetch projects: ${projectsRes.status}`);
    }

    const projects = await projectsRes.json();
    if (projects.length === 0) {
      // No projects available — open popup for manual entry
      chrome.action.openPopup();
      return;
    }

    // Save snippet to the first project
    const res = await fetch(`${apiUrl}/api/extension/snippet`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify({
        project_id: projects[0].id,
        type: "snippet",
        content: selectedText,
      }),
    });

    if (!res.ok) {
      throw new Error(`Failed to save snippet: ${res.status}`);
    }

    // Show a brief notification badge
    chrome.action.setBadgeText({ text: "OK", tabId: tab.id });
    chrome.action.setBadgeBackgroundColor({ color: "#7c9a6e", tabId: tab.id });
    setTimeout(() => {
      chrome.action.setBadgeText({ text: "", tabId: tab.id });
    }, 2000);
  } catch (err) {
    console.error("FlowTrack Clipper:", err.message);
    chrome.action.setBadgeText({ text: "!", tabId: tab.id });
    chrome.action.setBadgeBackgroundColor({ color: "#9b3232", tabId: tab.id });
    setTimeout(() => {
      chrome.action.setBadgeText({ text: "", tabId: tab.id });
    }, 3000);
  }
});
