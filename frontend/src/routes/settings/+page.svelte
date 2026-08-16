<script>
  import { onMount } from 'svelte';
  import { language, apiKey, showToast } from '$lib/stores.js';
  import { getConfigYaml, putConfigYaml, resetConfig, exportBackup, importBackup } from '$lib/api.js';
  import { t } from '$lib/i18n.js';
  import { tsFilename } from '$lib/utils.js';

  let yamlContent = '';
  let status = '';
  let statusType = '';
  let loading = true;
  let currentApiKey = '';

  apiKey.subscribe(v => currentApiKey = v);

  onMount(async () => {
    await loadConfig();
  });

  async function loadConfig() {
    loading = true;
    try {
      const data = await getConfigYaml();
      yamlContent = data.yaml || '';
      status = '';
    } catch (e) {
      status = 'Failed to load config: ' + e.message;
      statusType = 'error';
    } finally {
      loading = false;
    }
  }

  async function saveConfig() {
    try {
      await putConfigYaml(yamlContent);
      status = 'Configuration saved';
      statusType = 'success';
    } catch (e) {
      // Invalid YAML now comes back as a 422 with a problem+json detail rather
      // than a 200 carrying an { error } body.
      status = 'Save failed: ' + e.message;
      statusType = 'error';
    }
    setTimeout(() => status = '', 3000);
  }

  async function handleReset() {
    try {
      await resetConfig();
      await loadConfig();
      status = 'Configuration reset to defaults';
      statusType = 'success';
      setTimeout(() => status = '', 3000);
    } catch (e) { showToast(e.message); }
  }

  let importInput;
  let importStatus = '';
  let importStatusType = '';

  function handleApiKeyChange(e) {
    apiKey.set(e.target.value);
  }

  async function handleExportBackup() {
    try {
      const data = await exportBackup();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = tsFilename('flowtrack-backup', 'json');
      a.click();
      URL.revokeObjectURL(url);
      importStatus = 'Backup exported successfully';
      importStatusType = 'success';
    } catch (e) {
      importStatus = 'Export failed: ' + e.message;
      importStatusType = 'error';
    }
    setTimeout(() => importStatus = '', 3000);
  }

  async function handleImportBackup(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      const result = await importBackup(data);
      const i = result.imported;
      const s = result.skipped || {};
      const skippedTotal = Object.values(s).reduce((a, b) => a + b, 0);
      importStatus =
        `Imported: ${i.areas} areas, ${i.projects} projects, ${i.tasks} tasks, ${i.notes} notes, ${i.snippets} snippets` +
        (skippedTotal
          ? ` — skipped ${skippedTotal} record${skippedTotal === 1 ? '' : 's'} that already existed`
          : '');
      importStatusType = 'success';
    } catch (e) {
      importStatus = 'Import failed: ' + e.message;
      importStatusType = 'error';
    }
    if (importInput) importInput.value = '';
    setTimeout(() => importStatus = '', 5000);
  }
</script>

<div class="settings-page">
  <h1>{t('settings', $language)}</h1>
  <p class="settings-desc">
    Edit the YAML configuration below to set up LLM API keys, local model endpoints (Ollama, etc.),
    and IDE executable paths. Changes are stored on the server.
  </p>

  <div class="settings-section">
    <h2>API Key</h2>
    <p class="section-desc">The key used to authenticate with the FlowTrack API.</p>
    <input type="text" value={currentApiKey} on:change={handleApiKeyChange} placeholder="API Key" class="api-key-input" />
  </div>

  <div class="settings-section">
    <h2>Configuration (YAML)</h2>
    <p class="section-desc">
      Configure LLM providers, IDE paths, and CLI commands. Use <code>{'{project_dir}'}</code> as a placeholder
      for the project's local directory in IDE args.
    </p>

    {#if loading}
      <p class="loading-text">Loading configuration...</p>
    {:else}
      <textarea
        class="yaml-editor"
        bind:value={yamlContent}
        rows="30"
        spellcheck="false"
      ></textarea>

      <div class="settings-actions">
        <button class="primary" on:click={saveConfig}>{t('save', $language)}</button>
        <button on:click={handleReset}>Reset to Defaults</button>
      </div>
    {/if}

    {#if status}
      <div class="status-msg {statusType}">{status}</div>
    {/if}
  </div>

  <div class="settings-section">
    <h2>Backup &amp; Restore</h2>
    <p class="section-desc">
      Export all project data (areas, projects, tasks, notes, snippets) as a JSON file for backup or transfer.
      File attachments are not included — use the per-project ZIP export for that.
    </p>
    <div class="backup-actions">
      <button class="primary" on:click={handleExportBackup}>
        <svg viewBox="0 0 16 16" width="14" height="14" style="vertical-align: middle; margin-right: 4px;">
          <path d="M8 2v7M5 6l3 3 3-3M3 11v2h10v-2" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Export All Data (JSON)
      </button>
      <label class="import-label">
        <svg viewBox="0 0 16 16" width="14" height="14" style="vertical-align: middle; margin-right: 4px;">
          <path d="M8 10V3M5 6l3-3 3 3M3 11v2h10v-2" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Import Data (JSON)
        <input type="file" accept=".json" bind:this={importInput} on:change={handleImportBackup} hidden />
      </label>
    </div>
    {#if importStatus}
      <div class="status-msg {importStatusType}">{importStatus}</div>
    {/if}
  </div>

  <div class="settings-section">
    <h2>YAML Reference</h2>
    <pre class="reference">{`llm_providers:
  - name: OpenAI
    type: openai
    api_key: sk-...
    base_url: https://api.openai.com/v1
    model: gpt-4o
    enabled: true

  - name: Anthropic
    type: anthropic
    api_key: sk-ant-...
    model: claude-sonnet-4-20250514
    enabled: true

  - name: Ollama (local)
    type: ollama
    base_url: http://localhost:11434
    model: llama3
    enabled: true

ides:
  - name: Cursor
    command: C:/Users/you/AppData/Local/Programs/cursor/Cursor.exe
    args: ["{project_dir}"]

  - name: VS Code
    command: code
    args: ["{project_dir}"]

  - name: WebStorm
    command: C:/Program Files/JetBrains/WebStorm/bin/webstorm64.exe
    args: ["{project_dir}"]

cli:
  claude_command: claude`}</pre>
  </div>
</div>

<style>
  .settings-page {
    flex: 1;
    padding: 2rem;
    max-width: 800px;
    overflow-y: auto;
  }

  h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem; }
  h2 { font-size: 1rem; font-weight: 600; margin-bottom: 0.25rem; }

  .settings-desc {
    color: var(--text-secondary);
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
    line-height: 1.5;
  }

  .settings-section {
    margin-bottom: 2rem;
    padding: 1rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }

  .section-desc {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 0.75rem;
    line-height: 1.4;
  }

  .section-desc code {
    background: var(--bg-tertiary);
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
    font-family: var(--font-mono);
    font-size: 0.75rem;
  }

  .api-key-input {
    max-width: 400px;
  }

  .yaml-editor {
    font-family: var(--font-mono);
    font-size: 0.82rem;
    line-height: 1.5;
    width: 100%;
    min-height: 400px;
    resize: vertical;
    tab-size: 2;
    white-space: pre;
    overflow-x: auto;
  }

  .settings-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.75rem;
  }

  .status-msg {
    margin-top: 0.75rem;
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius);
    font-size: 0.85rem;
  }

  .status-msg.success { background: #e8f5e9; color: #2e7d32; }
  .status-msg.error { background: #ffebee; color: #c62828; }

  .reference {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    line-height: 1.5;
    background: var(--bg);
    padding: 0.75rem;
    border-radius: var(--radius);
    overflow-x: auto;
    white-space: pre;
    color: var(--text-secondary);
  }

  .loading-text { color: var(--text-muted); font-size: 0.85rem; }

  .backup-actions {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .import-label {
    display: inline-flex;
    align-items: center;
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg);
    color: var(--text);
    cursor: pointer;
    transition: all 0.2s;
  }

  .import-label:hover {
    background: var(--bg-tertiary);
    border-color: var(--accent);
  }
</style>
