<script>
  import { language, showToast } from '../stores.js';
  import { listNotes, createNote, updateNote, deleteNote } from '../api.js';
  import { t } from '../i18n.js';
  import { renderMarkdown } from '../markdown.js';
  import {
    ACTIONS,
    copyToClipboard,
    fallbackCommand,
    launch,
    launcherAvailable,
  } from '../launcher.js';
  import { onMount } from 'svelte';

  export let projectId = null;
  export let taskId = null;
  export let localDir = null;

  // Probed once. False simply means the buttons copy instead of launching.
  let hasLauncher = false;
  let openMenuFor = null;

  onMount(async () => {
    hasLauncher = await launcherAvailable();
  });

  function toggleMenu(noteId) {
    openMenuFor = openMenuFor === noteId ? null : noteId;
  }

  async function runAction(noteId, action) {
    openMenuFor = null;

    if (hasLauncher) {
      try {
        const { directory } = await launch({ action, projectId, noteId });
        showToast(`Opening a session in ${directory}`, 'success');
      } catch (e) {
        showToast(e.message);
      }
      return;
    }

    const command = fallbackCommand({ action, projectId, noteId, localDir });
    if (await copyToClipboard(command)) {
      showToast('No launcher running — command copied, paste it in a terminal', 'success');
    } else {
      showToast('No launcher running, and the clipboard is not available');
    }
  }

  let notes = [];
  let editingId = null;
  let editContent = '';
  let newContent = '';
  let showNew = false;

  async function load() {
    const params = {};
    if (projectId) params.project_id = projectId;
    if (taskId) params.task_id = taskId;
    try {
      notes = await listNotes(params);
    } catch (e) {
      showToast(e.message);
    }
  }

  async function handleCreate() {
    if (!newContent.trim()) return;
    try {
      const data = { content: newContent };
      if (projectId) data.project_id = projectId;
      if (taskId) data.task_id = taskId;
      await createNote(data);
      newContent = '';
      showNew = false;
      await load();
    } catch (e) {
      showToast(e.message);
    }
  }

  async function handleUpdate() {
    if (!editContent.trim()) return;
    try {
      await updateNote(editingId, editContent);
      editingId = null;
      await load();
    } catch (e) {
      showToast(e.message);
    }
  }

  async function handleDelete(id) {
    try {
      await deleteNote(id);
      await load();
    } catch (e) {
      showToast(e.message);
    }
  }

  function startEdit(note) {
    editingId = note.id;
    editContent = note.content;
  }

  $: (load(), projectId, taskId);
</script>

<div class="notes-section">
  <div class="notes-header">
    <h3>{t('notes', $language)}</h3>
    <button class="primary small" on:click={() => (showNew = !showNew)}
      >+ {t('newNote', $language)}</button
    >
  </div>

  {#if showNew}
    <div class="note-form">
      <textarea bind:value={newContent} placeholder="Write markdown..." rows="4"></textarea>
      <div class="form-actions">
        <button class="primary small" on:click={handleCreate}>{t('save', $language)}</button>
        <button class="small" on:click={() => (showNew = false)}>{t('cancel', $language)}</button>
      </div>
    </div>
  {/if}

  {#each notes as note}
    <div class="note-card">
      {#if editingId === note.id}
        <textarea bind:value={editContent} rows="4"></textarea>
        <div class="form-actions">
          <button class="primary small" on:click={handleUpdate}>{t('save', $language)}</button>
          <button class="small" on:click={() => (editingId = null)}>{t('cancel', $language)}</button
          >
        </div>
      {:else}
        <!-- renderMarkdown() HTML-escapes its input before applying its own tags, so no
             caller-supplied markup reaches the DOM. This matters: snippets arrive from
             arbitrary web pages via the clipper. -->
        <!-- eslint-disable-next-line svelte/no-at-html-tags -->
        <div class="note-content">{@html renderMarkdown(note.content)}</div>
        <div class="note-actions">
          {#if projectId && localDir}
            <div class="note-launch">
              <button class="icon-btn accent" on:click|stopPropagation={() => toggleMenu(note.id)}>
                {hasLauncher ? 'Open session' : 'Copy command'}
              </button>
              {#if openMenuFor === note.id}
                <div class="launch-menu" role="presentation" on:click|stopPropagation>
                  {#each Object.entries(ACTIONS) as [action, label]}
                    <button on:click={() => runAction(note.id, action)}>{label}</button>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}
          <button class="icon-btn" on:click={() => startEdit(note)}>Edit</button>
          <button class="icon-btn danger" on:click={() => handleDelete(note.id)}
            >{t('delete', $language)}</button
          >
          <span class="note-date">{new Date(note.created_at).toLocaleDateString()}</span>
        </div>
      {/if}
    </div>
  {/each}
</div>

<style>
  .notes-section {
    margin: 1rem 0;
  }

  .notes-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }

  .notes-header h3 {
    font-size: 1rem;
    font-weight: 600;
  }
  .small {
    font-size: 0.75rem;
    padding: 0.3rem 0.6rem;
  }

  .note-form {
    margin-bottom: 1rem;
    padding: 0.75rem;
    background: var(--bg-secondary);
    border-radius: var(--radius);
  }

  .form-actions {
    display: flex;
    gap: 0.25rem;
    margin-top: 0.5rem;
  }

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

  .note-launch {
    position: relative;
  }

  .icon-btn.accent {
    color: var(--text-secondary);
  }

  .launch-menu {
    position: absolute;
    bottom: 100%;
    left: 0;
    margin-bottom: 0.25rem;
    z-index: 10;
    display: flex;
    flex-direction: column;
    min-width: 9rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 3px;
    box-shadow: 0 2px 8px rgb(0 0 0 / 15%);
  }

  .launch-menu button {
    background: none;
    border: none;
    text-align: left;
    padding: 0.4rem 0.6rem;
    font-size: 0.78rem;
    color: var(--text-primary);
    cursor: pointer;
  }

  .launch-menu button:hover {
    background: var(--bg-primary);
  }

  .icon-btn {
    background: none;
    border: none;
    font-size: 0.75rem;
    color: var(--text-muted);
    padding: 0;
  }

  .icon-btn:hover {
    color: var(--accent);
  }
  .icon-btn.danger:hover {
    color: var(--danger);
  }

  .note-date {
    font-size: 0.7rem;
    color: var(--text-muted);
    margin-left: auto;
  }
</style>
