<script>
  import { language } from '../stores.js';
  import { listFiles, uploadFile, deleteFile } from '../api.js';
  import { t } from '../i18n.js';

  export let projectId;

  let files = [];
  let folder = '';
  let lang = 'en';
  let fileInput;

  language.subscribe(v => lang = v);

  async function load() {
    if (!projectId) return;
    files = await listFiles(projectId);
  }

  async function handleUpload(e) {
    const selected = e.target.files;
    if (!selected?.length) return;
    for (const file of selected) {
      await uploadFile(projectId, file, folder || null);
    }
    fileInput.value = '';
    await load();
  }

  async function handleDelete(fileId) {
    await deleteFile(projectId, fileId);
    await load();
  }

  function groupByFolder(fileList) {
    const groups = {};
    for (const f of fileList) {
      const key = f.folder || 'root';
      if (!groups[key]) groups[key] = [];
      groups[key].push(f);
    }
    return groups;
  }

  $: load(), projectId;
  $: grouped = groupByFolder(files);
</script>

<div class="file-manager">
  <div class="file-header">
    <h3>{t('files', lang)}</h3>
    <div class="upload-controls">
      <input type="text" bind:value={folder} placeholder="Folder (optional)" class="folder-input" />
      <label class="upload-btn primary">
        {t('uploadFile', lang)}
        <input type="file" multiple bind:this={fileInput} on:change={handleUpload} hidden />
      </label>
    </div>
  </div>

  {#if files.length === 0}
    <p class="empty">No files yet</p>
  {:else}
    {#each Object.entries(grouped) as [folderName, folderFiles]}
      <div class="file-group">
        <div class="folder-name">{folderName === 'root' ? 'Files' : folderName}</div>
        {#each folderFiles as file}
          <div class="file-item">
            <span class="file-type">{file.file_type}</span>
            <span class="file-name">{file.filename}</span>
            <span class="file-date">{new Date(file.created_at).toLocaleDateString()}</span>
            <button class="icon-btn danger" on:click={() => handleDelete(file.id)}>&#10005;</button>
          </div>
        {/each}
      </div>
    {/each}
  {/if}
</div>

<style>
  .file-manager { margin: 1rem 0; }

  .file-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .file-header h3 { font-size: 1rem; font-weight: 600; }

  .upload-controls {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .folder-input {
    width: 120px;
    font-size: 0.75rem;
    padding: 0.3rem 0.5rem;
  }

  .upload-btn {
    font-size: 0.75rem;
    padding: 0.3rem 0.6rem;
    border-radius: var(--radius);
    cursor: pointer;
    background: var(--accent);
    color: white;
    border: 1px solid var(--accent);
  }

  .file-group { margin-bottom: 0.75rem; }

  .folder-name {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    font-weight: 600;
    padding: 0.25rem 0;
  }

  .file-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.5rem;
    border-bottom: 1px solid var(--border);
    font-size: 0.85rem;
  }

  .file-type {
    font-size: 0.7rem;
    padding: 0.1rem 0.4rem;
    background: var(--bg-tertiary);
    border-radius: 3px;
    text-transform: uppercase;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .file-name { flex: 1; }
  .file-date { font-size: 0.7rem; color: var(--text-muted); }

  .icon-btn {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 0.8rem;
    padding: 0.2rem;
  }
  .icon-btn.danger:hover { color: var(--danger); }

  .empty { color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 1rem; }
</style>
