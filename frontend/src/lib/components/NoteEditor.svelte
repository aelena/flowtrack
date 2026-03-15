<script>
  import { language } from '../stores.js';
  import { listNotes, createNote, updateNote, deleteNote } from '../api.js';
  import { t } from '../i18n.js';
  import { renderMarkdown } from '../markdown.js';

  export let projectId = null;
  export let taskId = null;

  let notes = [];
  let editingId = null;
  let editContent = '';
  let newContent = '';
  let showNew = false;
  let lang = 'en';

  language.subscribe(v => lang = v);

  async function load() {
    const params = {};
    if (projectId) params.project_id = projectId;
    if (taskId) params.task_id = taskId;
    notes = await listNotes(params);
  }

  async function handleCreate() {
    if (!newContent.trim()) return;
    const data = { content: newContent };
    if (projectId) data.project_id = projectId;
    if (taskId) data.task_id = taskId;
    await createNote(data);
    newContent = '';
    showNew = false;
    await load();
  }

  async function handleUpdate() {
    if (!editContent.trim()) return;
    await updateNote(editingId, editContent);
    editingId = null;
    await load();
  }

  async function handleDelete(id) {
    await deleteNote(id);
    await load();
  }

  function startEdit(note) {
    editingId = note.id;
    editContent = note.content;
  }

  $: load(), projectId, taskId;
</script>

<div class="notes-section">
  <div class="notes-header">
    <h3>{t('notes', lang)}</h3>
    <button class="primary small" on:click={() => showNew = !showNew}>+ {t('newNote', lang)}</button>
  </div>

  {#if showNew}
    <div class="note-form">
      <textarea bind:value={newContent} placeholder="Write markdown..." rows="4"></textarea>
      <div class="form-actions">
        <button class="primary small" on:click={handleCreate}>{t('save', lang)}</button>
        <button class="small" on:click={() => showNew = false}>{t('cancel', lang)}</button>
      </div>
    </div>
  {/if}

  {#each notes as note}
    <div class="note-card">
      {#if editingId === note.id}
        <textarea bind:value={editContent} rows="4"></textarea>
        <div class="form-actions">
          <button class="primary small" on:click={handleUpdate}>{t('save', lang)}</button>
          <button class="small" on:click={() => editingId = null}>{t('cancel', lang)}</button>
        </div>
      {:else}
        <div class="note-content">{@html renderMarkdown(note.content)}</div>
        <div class="note-actions">
          <button class="icon-btn" on:click={() => startEdit(note)}>Edit</button>
          <button class="icon-btn danger" on:click={() => handleDelete(note.id)}>{t('delete', lang)}</button>
          <span class="note-date">{new Date(note.created_at).toLocaleDateString()}</span>
        </div>
      {/if}
    </div>
  {/each}
</div>

<style>
  .notes-section { margin: 1rem 0; }

  .notes-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }

  .notes-header h3 { font-size: 1rem; font-weight: 600; }
  .small { font-size: 0.75rem; padding: 0.3rem 0.6rem; }

  .note-form {
    margin-bottom: 1rem;
    padding: 0.75rem;
    background: var(--bg-secondary);
    border-radius: var(--radius);
  }

  .form-actions { display: flex; gap: 0.25rem; margin-top: 0.5rem; }

  .note-card {
    padding: 0.75rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    margin-bottom: 0.5rem;
  }

  .note-content {
    font-size: 0.9rem;
    line-height: 1.5;
  }

  .note-content :global(code) {
    background: var(--bg-tertiary);
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
    font-family: var(--font-mono);
    font-size: 0.8rem;
  }

  .note-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.5rem;
    align-items: center;
  }

  .icon-btn {
    background: none;
    border: none;
    font-size: 0.75rem;
    color: var(--text-muted);
    padding: 0;
  }

  .icon-btn:hover { color: var(--accent); }
  .icon-btn.danger:hover { color: var(--danger); }

  .note-date {
    font-size: 0.7rem;
    color: var(--text-muted);
    margin-left: auto;
  }
</style>
