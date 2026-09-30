// ── Context menu setup ───────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save-to-flowtrack",
    title: "Save to FlowTrack",
    contexts: ["selection"],
  });
});

// ── Badge feedback ───────────────────────────────────────

function flashBadge(tabId, text, color, ms) {
  chrome.action.setBadgeText({ text, tabId });
  chrome.action.setBadgeBackgroundColor({ color, tabId });
  setTimeout(() => {
    chrome.action.setBadgeText({ text: "", tabId });
  }, ms);
}

// ── Context menu handler ─────────────────────────────────

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "save-to-flowtrack") return;

  const selectedText = info.selectionText;
  if (!selectedText) return;

  const data = await chrome.storage.local.get(["apiUrl", "apiKey", "defaultProjectId"]);
  const apiUrl = data.apiUrl?.replace(/\/+$/, "");
  const apiKey = data.apiKey;

  if (!apiUrl || !apiKey) {
    // No settings configured — open the popup so the user can configure
    chrome.action.openPopup();
    return;
  }

  // Right-click has no project picker, so it clips to whatever the popup last
  // chose. Guessing instead — the first project in the list, as this once did —
  // files the clip somewhere the user never named and still reports success.
  // Nothing chosen, or the Inbox chosen, sends null: the API files it in the
  // Inbox, which is the whole point of being able to clip an idea on sight.
  const projectId =
    !data.defaultProjectId || data.defaultProjectId === "__inbox__" ? null : data.defaultProjectId;

  try {
    const res = await fetch(`${apiUrl}/api/extension/snippet`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify({
        project_id: projectId,
        type: "snippet",
        content: selectedText,
        source_url: info.pageUrl || tab?.url || null,
      }),
    });

    if (!res.ok) {
      throw new Error(`Failed to save snippet: ${res.status}`);
    }

    flashBadge(tab.id, "OK", "#7c9a6e", 2000);
  } catch (err) {
    console.error("FlowTrack Clipper:", err.message);
    flashBadge(tab.id, "!", "#9b3232", 3000);
  }
});
