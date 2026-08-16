<script>
  import { onMount } from 'svelte';
  import { language, showToast } from '../stores.js';
  import { getProject, updateProject, setProjectArchived, listFiles, uploadFile, deleteFile } from '../api.js';
  import { t } from '../i18n.js';
  import TaskList from './TaskList.svelte';
  import NoteEditor from './NoteEditor.svelte';
  import WriteMode from './WriteMode.svelte';
  import ChatMode from './ChatMode.svelte';
  import CommandBar from './CommandBar.svelte';

  export let projectId;

  let project = null;
  let mode = 'overview';
  let editing = false;
  let editData = {};
  let writeContent = '';

  // File tree state
  let files = [];
  let fileFolder = '';
  let fileInput;
  let collapsedFileFolders = {};

  // Tag editing
  let newTag = '';
  let showTagInput = false;

  async function load() {
    if (!projectId) return;
    try {
      project = await getProject(projectId);
      writeContent = project.description || '';
      await loadFiles();
    } catch (e) { showToast(e.message); }
  }

  async function loadFiles() {
    if (!projectId) return;
    try {
      files = await listFiles(projectId);
    } catch { files = []; }
  }

  // Convert empty strings to null for nullable fields
  function cleanEditData(data) {
    const nullable = [
      'final_name', 'description', 'vision', 'goal',
      'completion_criteria', 'abandonment_criteria',
      'desired_end_date', 'github_repo', 'website', 'local_dir'
    ];
    const cleaned = { ...data };
    for (const key of nullable) {
      if (cleaned[key] === '') cleaned[key] = null;
    }
    return cleaned;
  }

  async function save() {
    try {
      await updateProject(projectId, cleanEditData(editData));
      editing = false;
      await load();
    } catch (e) {
      showToast(e.message);
    }
  }

  function startEdit() {
    editData = {
      work_name: project.work_name,
      final_name: project.final_name || '',
      description: project.description || '',
      vision: project.vision || '',
      goal: project.goal || '',
      completion_criteria: project.completion_criteria || '',
      abandonment_criteria: project.abandonment_criteria || '',
      desired_end_date: project.desired_end_date || '',
      github_repo: project.github_repo || '',
      website: project.website || '',
      local_dir: project.local_dir || '',
      subjective_completion: project.subjective_completion,
    };
    editing = true;
  }

  async function setRating(n) {
    try {
      await updateProject(projectId, { star_rating: n });
      await load();
    } catch (e) { showToast(e.message); }
  }

  async function handleArchive() {
    try {
      // The button already offered "Unarchive" for archived projects but always
      // called archive, so there was no way back out of the archive.
      await setProjectArchived(projectId, !project.archived);
      await load();
    } catch (e) { showToast(e.message); }
  }

  async function addTag() {
    const tag = newTag.trim().toLowerCase();
    if (!tag || (project.tags || []).includes(tag)) { newTag = ''; return; }
    try {
      const tags = [...(project.tags || []), tag];
      await updateProject(projectId, { tags });
      newTag = '';
      showTagInput = false;
      await load();
    } catch (e) { showToast(e.message); }
  }

  async function removeTag(tag) {
    try {
      const tags = (project.tags || []).filter(t => t !== tag);
      await updateProject(projectId, { tags });
      await load();
    } catch (e) { showToast(e.message); }
  }

  // File tree actions
  async function handleFileUpload(e) {
    const selected = e.target.files;
    if (!selected?.length) return;
    try {
      for (const file of selected) {
        await uploadFile(projectId, file, fileFolder || null);
      }
      fileInput.value = '';
      await loadFiles();
    } catch (err) { showToast(err.message); }
  }

  async function handleFileDelete(fileId) {
    try {
      await deleteFile(projectId, fileId);
      await loadFiles();
    } catch (e) { showToast(e.message); }
  }

  function toggleFileFolder(name) {
    collapsedFileFolders[name] = !collapsedFileFolders[name];
    collapsedFileFolders = collapsedFileFolders;
  }

  function groupFilesByFolder(fileList) {
    const groups = {};
    for (const f of fileList) {
      const key = f.folder || '';
      if (!groups[key]) groups[key] = [];
      groups[key].push(f);
    }
    return groups;
  }

  function fileIcon(type) {
    if (type === 'md') return '📝';
    if (type === 'pdf') return '📄';
    if (type === 'docx' || type === 'doc') return '📃';
    if (type === 'json') return '{ }';
    if (type === 'yaml' || type === 'yml') return '⚙';
    return '📎';
  }

  $: if (projectId) load();
  $: groupedFiles = groupFilesByFolder(files);
  $: fileFolderNames = Object.keys(groupedFiles).sort((a, b) => {
    if (a === '') return 1;
    if (b === '') return -1;
    return a.localeCompare(b);
  });
</script>

{#if project}
<div class="project-page">
  <!-- Main content area -->
  <div class="project-main">
    <header class="project-header">
      <div class="header-top">
        <div>
          <h1>{project.work_name}</h1>
          {#if project.final_name}
            <span class="final-name">{project.final_name}</span>
          {/if}
          {#if project.status && project.status !== 'active'}
            <span class="status-badge {project.status}">{project.status === 'on_hold' ? 'On Hold' : 'Deprecated'}</span>
          {/if}
        </div>
        <div class="header-actions">
          <button on:click={startEdit}>Edit</button>
          <button on:click={handleArchive}>{project.archived ? 'Unarchive' : t('archive', $language)}</button>
        </div>
      </div>

      <div class="stars">
        {#each [1,2,3,4,5] as n}
          <span class:active={project.star_rating >= n} on:click={() => setRating(n)}>★</span>
        {/each}
      </div>

      <div class="tag-row">
        {#each (project.tags || []) as tag}
          <span class="tag-pill">
            {tag}
            <button class="tag-remove" on:click={() => removeTag(tag)}>×</button>
          </span>
        {/each}
        {#if showTagInput}
          <input
            class="tag-input"
            type="text"
            bind:value={newTag}
            placeholder="tag name"
            on:keydown={(e) => { if (e.key === 'Enter') addTag(); if (e.key === 'Escape') { showTagInput = false; newTag = ''; } }}
            on:blur={() => { if (!newTag.trim()) showTagInput = false; }}
          />
        {:else}
          <button class="tag-add" on:click={() => showTagInput = true}>+ tag</button>
        {/if}
      </div>

      <div class="progress-row">
        <div class="progress-item">
          <span class="progress-label">{t('completion', $language)}: {project.task_completion}%</span>
          <div class="progress-bar"><div class="fill" style="width: {project.task_completion}%"></div></div>
        </div>
        <div class="progress-item">
          <span class="progress-label">{t('subjective', $language)}: {project.subjective_completion}%</span>
          <div class="progress-bar"><div class="fill subjective-fill" style="width: {project.subjective_completion}%"></div></div>
        </div>
      </div>

      <div class="mode-tabs">
        <button class:active={mode === 'overview' && !editing} on:click={() => { editing = false; mode = 'overview'; }}>Overview</button>
        <button class:active={mode === 'write' && !editing} on:click={() => { editing = false; mode = 'write'; }}>{t('writeMode', $language)}</button>
        <button class:active={mode === 'chat' && !editing} on:click={() => { editing = false; mode = 'chat'; }}>{t('chatMode', $language)}</button>
        {#if editing}
          <span class="mode-editing">Editing</span>
        {/if}
      </div>
    </header>

    {#if editing}
      <div class="edit-form">
        <label>Work Name <input type="text" bind:value={editData.work_name} /></label>
        <label>Final Name <input type="text" bind:value={editData.final_name} /></label>
        <label>{t('description', $language)} <textarea bind:value={editData.description} rows="3"></textarea></label>
        <label>{t('vision', $language)} <textarea bind:value={editData.vision} rows="2"></textarea></label>
        <label>{t('goal', $language)} <textarea bind:value={editData.goal} rows="2"></textarea></label>
        <label>Completion Criteria <textarea bind:value={editData.completion_criteria} rows="2"></textarea></label>
        <label>Abandonment Criteria <textarea bind:value={editData.abandonment_criteria} rows="2"></textarea></label>
        <label>Desired End Date <input type="date" bind:value={editData.desired_end_date} /></label>
        <label>GitHub Repo <input type="text" bind:value={editData.github_repo} /></label>
        <label>Website <input type="text" bind:value={editData.website} /></label>
        <label>Local Directory <input type="text" bind:value={editData.local_dir} /></label>
        <label>Subjective Completion (%) <input type="number" min="0" max="100" bind:value={editData.subjective_completion} /></label>
        <div class="form-actions">
          <button class="primary" on:click={save}>{t('save', $language)}</button>
          <button on:click={() => editing = false}>{t('cancel', $language)}</button>
        </div>
      </div>
    {:else if mode === 'overview'}
      <div class="project-details">
        {#if project.description}
          <section><h3>{t('description', $language)}</h3><p>{project.description}</p></section>
        {/if}
        {#if project.vision}
          <section><h3>{t('vision', $language)}</h3><p>{project.vision}</p></section>
        {/if}
        {#if project.goal}
          <section><h3>{t('goal', $language)}</h3><p>{project.goal}</p></section>
        {/if}
        {#if project.github_repo}
          <section><span class="meta-label">GitHub:</span> <a href={project.github_repo} target="_blank">{project.github_repo}</a></section>
        {/if}
        {#if project.website}
          <section><span class="meta-label">Website:</span> <a href={project.website} target="_blank">{project.website}</a></section>
        {/if}
        {#if project.desired_end_date}
          <section><span class="meta-label">Target Date:</span> {project.desired_end_date}</section>
        {/if}
        {#if project.collaborators?.length}
          <section>
            <span class="meta-label">{t('collaborators', $language)}:</span>
            {project.collaborators.map(c => typeof c === 'string' ? c : c.name || JSON.stringify(c)).join(', ')}
          </section>
        {/if}

        <TaskList {projectId} />
        <NoteEditor {projectId} />
        <CommandBar {projectId} localDir={project.local_dir || ''} projectName={project.work_name} />
      </div>
    {:else if mode === 'write'}
      <WriteMode bind:content={writeContent} onSave={(c) => updateProject(projectId, { description: c })} />
    {:else if mode === 'chat'}
      <ChatMode {projectId} />
    {/if}
  </div>

  <!-- Right panel: File tree -->
  <aside class="file-panel">
    <div class="file-panel-header">
      <h3>{t('files', $language)}</h3>
    </div>

    <div class="file-upload-row">
      <input type="text" bind:value={fileFolder} placeholder="Folder" class="folder-input" />
      <label class="upload-label">
        + Upload
        <input type="file" multiple bind:this={fileInput} on:change={handleFileUpload} hidden />
      </label>
    </div>

    <div class="file-tree">
      {#if files.length === 0}
        <p class="file-empty">No files yet. Upload PDFs, DOCX, or .md files to associate with this project.</p>
      {:else}
        {#each fileFolderNames as folderName}
          {@const folderFiles = groupedFiles[folderName]}
          {@const displayName = folderName || 'Root'}
          <div class="file-folder">
            {#if folderName}
              <button class="file-folder-header" on:click={() => toggleFileFolder(folderName)}>
                <span class="folder-chevron">{collapsedFileFolders[folderName] ? '▶' : '▼'}</span>
                <svg viewBox="0 0 16 16" class="folder-icon"><path d="M2 3h4l2 2h6v8H2z" fill="currentColor" opacity="0.6"/></svg>
                <span>{displayName}</span>
                <span class="file-folder-count">{folderFiles.length}</span>
              </button>
            {:else}
              <div class="file-folder-header root">
                <svg viewBox="0 0 16 16" class="folder-icon"><path d="M2 3h4l2 2h6v8H2z" fill="currentColor" opacity="0.6"/></svg>
                <span>Files</span>
                <span class="file-folder-count">{folderFiles.length}</span>
              </div>
            {/if}

            {#if !collapsedFileFolders[folderName]}
              {#each folderFiles as file}
                <div class="file-tree-item">
                  <span class="file-icon">{fileIcon(file.file_type)}</span>
                  <span class="file-tree-name" title={file.filename}>{file.filename}</span>
                  <span class="file-tree-type">{file.file_type}</span>
                  <button class="file-tree-action" on:click={() => handleFileDelete(file.id)} title="Remove">×</button>
                </div>
              {/each}
            {/if}
          </div>
        {/each}
      {/if}
    </div>
  </aside>
</div>
{:else}
  <div class="loading">Loading project...</div>
{/if}

<style>
  .project-page {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  /* Main content */
  .project-main {
    flex: 1;
    padding: 1.5rem;
    overflow-y: auto;
    min-width: 0;
  }

  .project-header { margin-bottom: 1.5rem; }
  .header-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }
  h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
  .final-name { font-size: 0.85rem; color: var(--text-secondary); font-style: italic; }
  .status-badge { font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 10px; font-weight: 600; margin-left: 0.5rem; display: inline-block; vertical-align: middle; }
  .status-badge.on_hold { background: var(--warning); color: white; }
  .status-badge.deprecated { background: var(--text-muted); color: white; }
  .header-actions { display: flex; gap: 0.5rem; flex-shrink: 0; }
  .tag-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    align-items: center;
    margin: 0.5rem 0;
  }
  .tag-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    padding: 0.15rem 0.5rem;
    background: var(--bg-tertiary);
    border-radius: 12px;
    font-size: 0.75rem;
    color: var(--text-secondary);
  }
  .tag-remove {
    background: none;
    border: none;
    font-size: 0.8rem;
    color: var(--text-muted);
    cursor: pointer;
    padding: 0;
    line-height: 1;
  }
  .tag-remove:hover { color: var(--danger); }
  .tag-add {
    background: none;
    border: 1px dashed var(--border);
    border-radius: 12px;
    padding: 0.15rem 0.5rem;
    font-size: 0.7rem;
    color: var(--text-muted);
    cursor: pointer;
  }
  .tag-add:hover { border-color: var(--accent); color: var(--accent); }
  .tag-input {
    width: 100px;
    font-size: 0.75rem;
    padding: 0.15rem 0.4rem;
    border-radius: 12px;
  }

  .progress-row { display: flex; gap: 1.5rem; margin: 0.75rem 0; }
  .progress-item { flex: 1; }
  .progress-label { font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.25rem; display: block; }

  .mode-tabs { display: flex; gap: 0; border-bottom: 2px solid var(--border); margin-top: 0.75rem; }
  .mode-tabs button { border: none; border-bottom: 2px solid transparent; border-radius: 0; background: none; padding: 0.5rem 1rem; font-size: 0.85rem; color: var(--text-secondary); margin-bottom: -2px; }
  .mode-tabs button.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
  .mode-editing { font-size: 0.75rem; color: var(--warning); font-weight: 600; margin-left: auto; align-self: center; }

  .subjective-fill { background: #e89b3e; }

  .project-details section { margin-bottom: 0.75rem; }
  .project-details h3 { font-size: 0.9rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.25rem; }
  .project-details p { font-size: 0.9rem; line-height: 1.5; }
  .meta-label { font-weight: 600; font-size: 0.85rem; color: var(--text-secondary); }

  .edit-form { display: flex; flex-direction: column; gap: 0.75rem; }
  .edit-form label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); }
  .form-actions { display: flex; gap: 0.5rem; margin-top: 0.5rem; }
  .loading { padding: 2rem; text-align: center; color: var(--text-muted); }

  /* Right file panel */
  .file-panel {
    width: 260px;
    min-width: 260px;
    border-left: 1px solid var(--border);
    background: var(--bg-secondary);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .file-panel-header {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border);
  }

  .file-panel-header h3 {
    font-size: 0.85rem;
    font-weight: 600;
    margin: 0;
  }

  .file-upload-row {
    display: flex;
    gap: 0.4rem;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--border);
  }

  .folder-input {
    flex: 1;
    font-size: 0.7rem;
    padding: 0.25rem 0.4rem;
    min-width: 0;
  }

  .upload-label {
    font-size: 0.7rem;
    padding: 0.25rem 0.5rem;
    background: var(--accent);
    color: white;
    border-radius: var(--radius);
    cursor: pointer;
    white-space: nowrap;
    display: flex;
    align-items: center;
  }

  .upload-label:hover { background: var(--accent-hover); }

  .file-tree {
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem 0;
  }

  .file-empty {
    padding: 1rem;
    font-size: 0.75rem;
    color: var(--text-muted);
    text-align: center;
    line-height: 1.5;
  }

  .file-folder { margin-bottom: 0.25rem; }

  .file-folder-header {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.3rem 0.75rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-secondary);
    background: none;
    border: none;
    width: 100%;
    text-align: left;
    cursor: pointer;
  }

  .file-folder-header.root {
    cursor: default;
  }

  .file-folder-header:hover { background: var(--bg-tertiary); }

  .folder-chevron { font-size: 0.55rem; width: 10px; text-align: center; }
  .folder-icon { width: 14px; height: 14px; color: var(--accent); flex-shrink: 0; }
  .file-folder-count { font-size: 0.6rem; color: var(--text-muted); margin-left: auto; }

  .file-tree-item {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.25rem 0.75rem 0.25rem 1.8rem;
    font-size: 0.78rem;
  }

  .file-tree-item:hover { background: var(--bg-tertiary); }

  .file-icon { font-size: 0.75rem; flex-shrink: 0; width: 16px; text-align: center; }

  .file-tree-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text);
  }

  .file-tree-type {
    font-size: 0.6rem;
    padding: 0.05rem 0.3rem;
    background: var(--bg-tertiary);
    border-radius: 3px;
    color: var(--text-muted);
    text-transform: uppercase;
    font-weight: 600;
    flex-shrink: 0;
  }

  .file-tree-action {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 0.8rem;
    padding: 0 0.15rem;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.15s;
    flex-shrink: 0;
  }

  .file-tree-item:hover .file-tree-action { opacity: 1; }
  .file-tree-action:hover { color: var(--danger); }
</style>
