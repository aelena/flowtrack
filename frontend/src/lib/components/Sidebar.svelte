<script>
  import { onMount } from 'svelte';
  import { projects, areas, sidebarOpen, language, showToast } from '../stores.js';
  import { listProjects, listAreas, getAllTags, createProject, createArea, updateArea, deleteArea, updateProject, archiveProject, exportProject } from '../api.js';
  import { t } from '../i18n.js';
  import { tsFilename } from '../utils.js';
  import { goto } from '$app/navigation';

  let search = '';
  let filterArea = '';
  let filterTag = '';
  let allTags = [];
  let sortBy = 'created_at';
  let sortOrder = 'desc';
  let showArchived = false;
  let showNewProject = false;
  let showNewArea = false;
  let newProjectName = '';
  let newAreaName = '';

  let editingAreaId = null;
  let editingAreaName = '';
  let dragProjectId = null;
  let collapsedAreas = {};
  let activeMenu = null; // project id with open action menu

  onMount(() => { loadData(); });

  async function loadData() {
    try {
      const params = { sort_by: sortBy, sort_order: sortOrder, archived: showArchived };
      if (search) params.search = search;
      if (filterArea) params.area_id = filterArea;
      if (filterTag) params.tag = filterTag;
      const [p, a, t] = await Promise.all([listProjects(params), listAreas(), getAllTags()]);
      projects.set(p);
      areas.set(a);
      allTags = t || [];
    } catch (e) {
      console.error('Failed to load data:', e);
    }
  }

  async function handleCreateProject() {
    if (!newProjectName.trim()) return;
    try {
      const created = await createProject({ work_name: newProjectName });
      newProjectName = '';
      showNewProject = false;
      await loadData();
      if (created?.id) goto(`/projects/${created.id}`);
    } catch (e) { showToast(e.message); }
  }

  async function handleCreateArea() {
    if (!newAreaName.trim()) return;
    try {
      await createArea(newAreaName);
      newAreaName = '';
      showNewArea = false;
      await loadData();
    } catch (e) { showToast(e.message); }
  }

  async function handleRenameArea(areaId) {
    if (!editingAreaName.trim()) return;
    try {
      await updateArea(areaId, editingAreaName);
      editingAreaId = null;
      editingAreaName = '';
      await loadData();
    } catch (e) { showToast(e.message); }
  }

  async function handleDeleteArea(areaId) {
    try {
      await deleteArea(areaId);
      await loadData();
    } catch (e) { showToast(e.message); }
  }

  function selectProject(id) {
    activeMenu = null;
    goto(`/projects/${id}`);
  }

  function toggleArea(areaId) {
    collapsedAreas[areaId] = !collapsedAreas[areaId];
    collapsedAreas = collapsedAreas;
  }

  function toggleMenu(e, projectId) {
    e.stopPropagation();
    activeMenu = activeMenu === projectId ? null : projectId;
  }

  function closeMenus() {
    activeMenu = null;
  }

  // Project quick actions
  async function quickArchive(e, projectId) {
    e.stopPropagation();
    activeMenu = null;
    try {
      await archiveProject(projectId);
      await loadData();
    } catch (err) { showToast(err.message); }
  }

  async function quickExport(e, projectId, projectName) {
    e.stopPropagation();
    activeMenu = null;
    try {
      const blob = await exportProject(projectId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = tsFilename(projectName, 'zip');
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) { showToast(err.message); }
  }

  async function quickSetStatus(e, projectId, status) {
    e.stopPropagation();
    activeMenu = null;
    try {
      await updateProject(projectId, { status });
      await loadData();
    } catch (err) { showToast(err.message); }
  }

  // Drag and drop
  function onDragStart(e, projectId) {
    dragProjectId = projectId;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', projectId);
  }
  function onDragOver(e) { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }
  async function onDropToArea(e, areaId) {
    e.preventDefault();
    const pid = e.dataTransfer.getData('text/plain') || dragProjectId;
    if (!pid) return;
    try {
      await updateProject(pid, { area_id: areaId });
      dragProjectId = null;
      await loadData();
    } catch (err) { showToast(err.message); dragProjectId = null; }
  }
  async function onDropToUngrouped(e) {
    e.preventDefault();
    const pid = e.dataTransfer.getData('text/plain') || dragProjectId;
    if (!pid) return;
    try {
      await updateProject(pid, { area_id: null });
      dragProjectId = null;
      await loadData();
    } catch (err) { showToast(err.message); dragProjectId = null; }
  }
  function onDragEnd() { dragProjectId = null; }

  function groupByArea(projectList, areaList) {
    const grouped = {};
    for (const a of areaList) grouped[a.id] = [];
    const ungrouped = [];
    for (const p of projectList) {
      if (p.area_id && grouped[p.area_id]) grouped[p.area_id].push(p);
      else ungrouped.push(p);
    }
    return { grouped, ungrouped };
  }

  function statusIcon(status) {
    if (status === 'on_hold') return '⏸';
    if (status === 'deprecated') return '⊘';
    return '';
  }

  function doSearch() { loadData(); }

  $: groups = groupByArea($projects, $areas);
</script>

<svelte:window on:click={closeMenus} />

{#if $sidebarOpen}
<aside class="sidebar">
  <div class="sidebar-header">
    <h2>{t('projects', $language)}</h2>
    <button class="icon-btn" on:click={() => sidebarOpen.set(false)} title="Collapse sidebar">←</button>
  </div>

  <input type="text" placeholder={t('search', $language)} bind:value={search} on:input={doSearch} />

  <div class="sidebar-controls">
    <select bind:value={filterArea} on:change={doSearch}>
      <option value="">All {t('areas', $language)}</option>
      {#each $areas as area}
        <option value={area.id}>{area.name}</option>
      {/each}
    </select>
    <select bind:value={sortBy} on:change={doSearch}>
      <option value="created_at">Date</option>
      <option value="work_name">Name</option>
    </select>
    <button class="icon-btn small" on:click={() => { sortOrder = sortOrder === 'asc' ? 'desc' : 'asc'; doSearch(); }}>
      {sortOrder === 'asc' ? '\u25B2' : '\u25BC'}
    </button>
  </div>

  {#if allTags.length > 0}
    <div class="tag-filter">
      <select bind:value={filterTag} on:change={doSearch}>
        <option value="">All Tags</option>
        {#each allTags as tag}
          <option value={tag}>{tag}</option>
        {/each}
      </select>
      {#if filterTag}
        <button class="tag-clear" on:click={() => { filterTag = ''; doSearch(); }} title="Clear tag filter">×</button>
      {/if}
    </div>
  {/if}

  <div class="sidebar-actions">
    <button class="primary small" on:click={() => showNewProject = true}>+ Project</button>
    <button class="small" on:click={() => showNewArea = true}>+ Folder</button>
  </div>

  {#if showNewProject}
    <div class="inline-form">
      <input type="text" bind:value={newProjectName} placeholder="Project name" on:keydown={(e) => e.key === 'Enter' && handleCreateProject()} />
      <div class="inline-actions">
        <button class="primary small" on:click={handleCreateProject}>{t('save', $language)}</button>
        <button class="small" on:click={() => showNewProject = false}>{t('cancel', $language)}</button>
      </div>
    </div>
  {/if}

  {#if showNewArea}
    <div class="inline-form">
      <input type="text" bind:value={newAreaName} placeholder="Folder name" on:keydown={(e) => e.key === 'Enter' && handleCreateArea()} />
      <div class="inline-actions">
        <button class="primary small" on:click={handleCreateArea}>{t('save', $language)}</button>
        <button class="small" on:click={() => showNewArea = false}>{t('cancel', $language)}</button>
      </div>
    </div>
  {/if}

  <nav class="project-tree">
    {#each $areas as area (area.id)}
      <div class="tree-group" class:drop-target={dragProjectId} on:dragover={onDragOver} on:drop={(e) => onDropToArea(e, area.id)}>
        <div class="tree-group-header">
          <button class="folder-toggle" on:click={() => toggleArea(area.id)}>{collapsedAreas[area.id] ? '▶' : '▼'}</button>
          {#if editingAreaId === area.id}
            <input class="rename-input" type="text" bind:value={editingAreaName}
              on:keydown={(e) => { if (e.key === 'Enter') handleRenameArea(area.id); if (e.key === 'Escape') editingAreaId = null; }}
              on:blur={() => editingAreaId = null} />
          {:else}
            <span class="folder-name">{area.name}</span>
            <span class="folder-count">{groups.grouped[area.id]?.length || 0}</span>
          {/if}
          <div class="folder-actions">
            <button class="folder-btn" on:click|stopPropagation={() => { editingAreaId = area.id; editingAreaName = area.name; }} title="Rename">✎</button>
            <button class="folder-btn danger" on:click|stopPropagation={() => handleDeleteArea(area.id)} title="Delete folder">×</button>
          </div>
        </div>
        {#if !collapsedAreas[area.id]}
          {#each groups.grouped[area.id] || [] as project (project.id)}
            {@const si = statusIcon(project.status)}
            <div class="tree-item-row">
              <button class="tree-item" draggable="true"
                on:dragstart={(e) => onDragStart(e, project.id)} on:dragend={onDragEnd}
                on:click={() => selectProject(project.id)}
                class:dimmed={project.status === 'on_hold' || project.status === 'deprecated'}>
                <span class="drag-handle">⠿</span>
                {#if si}<span class="status-icon">{si}</span>{/if}
                <span class="project-name">{project.work_name}</span>
                {#if project.tags?.length}<span class="mini-tags">{#each project.tags.slice(0, 2) as tag}<span class="mini-tag">{tag}</span>{/each}</span>{/if}
                {#if project.star_rating}<span class="mini-stars">{'\u2605'.repeat(project.star_rating)}</span>{/if}
              </button>
              <button class="action-trigger" on:click={(e) => toggleMenu(e, project.id)} title="Actions">⋯</button>
              {#if activeMenu === project.id}
                <div class="action-menu" on:click|stopPropagation>
                  <button on:click={(e) => quickArchive(e, project.id)}>
                    <svg viewBox="0 0 16 16" class="menu-icon"><path d="M2 3h12v2H2zm1 3h10v7H3zm4 2v3h2V8z" fill="currentColor"/></svg>
                    Archive
                  </button>
                  <button on:click={(e) => quickExport(e, project.id, project.work_name)}>
                    <svg viewBox="0 0 16 16" class="menu-icon"><path d="M8 2v7M5 6l3 3 3-3M3 11v2h10v-2" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    Download ZIP
                  </button>
                  {#if project.status !== 'on_hold'}
                    <button on:click={(e) => quickSetStatus(e, project.id, 'on_hold')}>
                      <svg viewBox="0 0 16 16" class="menu-icon"><rect x="4" y="3" width="3" height="10" rx="1" fill="currentColor"/><rect x="9" y="3" width="3" height="10" rx="1" fill="currentColor"/></svg>
                      On Hold
                    </button>
                  {:else}
                    <button on:click={(e) => quickSetStatus(e, project.id, 'active')}>
                      <svg viewBox="0 0 16 16" class="menu-icon"><polygon points="4,2 14,8 4,14" fill="currentColor"/></svg>
                      Reactivate
                    </button>
                  {/if}
                  {#if project.status !== 'deprecated'}
                    <button class="danger-action" on:click={(e) => quickSetStatus(e, project.id, 'deprecated')}>
                      <svg viewBox="0 0 16 16" class="menu-icon"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5" fill="none"/><line x1="4" y1="4" x2="12" y2="12" stroke="currentColor" stroke-width="1.5"/></svg>
                      Deprecated
                    </button>
                  {:else}
                    <button on:click={(e) => quickSetStatus(e, project.id, 'active')}>
                      <svg viewBox="0 0 16 16" class="menu-icon"><polygon points="4,2 14,8 4,14" fill="currentColor"/></svg>
                      Reactivate
                    </button>
                  {/if}
                </div>
              {/if}
            </div>
          {/each}
          {#if (groups.grouped[area.id]?.length || 0) === 0}
            <p class="empty-folder">Drop projects here</p>
          {/if}
        {/if}
      </div>
    {/each}

    <!-- Ungrouped -->
    <div class="tree-group" class:drop-target={dragProjectId} on:dragover={onDragOver} on:drop={onDropToUngrouped}>
      <div class="tree-group-header">
        <span class="folder-name">Ungrouped</span>
        <span class="folder-count">{groups.ungrouped.length}</span>
      </div>
      {#each groups.ungrouped as project (project.id)}
        {@const si = statusIcon(project.status)}
        <div class="tree-item-row">
          <button class="tree-item" draggable="true"
            on:dragstart={(e) => onDragStart(e, project.id)} on:dragend={onDragEnd}
            on:click={() => selectProject(project.id)}
            class:dimmed={project.status === 'on_hold' || project.status === 'deprecated'}>
            <span class="drag-handle">⠿</span>
            {#if si}<span class="status-icon">{si}</span>{/if}
            <span class="project-name">{project.work_name}</span>
            {#if project.star_rating}<span class="mini-stars">{'\u2605'.repeat(project.star_rating)}</span>{/if}
          </button>
          <button class="action-trigger" on:click={(e) => toggleMenu(e, project.id)} title="Actions">⋯</button>
          {#if activeMenu === project.id}
            <div class="action-menu" on:click|stopPropagation>
              <button on:click={(e) => quickArchive(e, project.id)}>
                <svg viewBox="0 0 16 16" class="menu-icon"><path d="M2 3h12v2H2zm1 3h10v7H3zm4 2v3h2V8z" fill="currentColor"/></svg>
                Archive
              </button>
              <button on:click={(e) => quickExport(e, project.id, project.work_name)}>
                <svg viewBox="0 0 16 16" class="menu-icon"><path d="M8 2v7M5 6l3 3 3-3M3 11v2h10v-2" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
                Download ZIP
              </button>
              {#if project.status !== 'on_hold'}
                <button on:click={(e) => quickSetStatus(e, project.id, 'on_hold')}>
                  <svg viewBox="0 0 16 16" class="menu-icon"><rect x="4" y="3" width="3" height="10" rx="1" fill="currentColor"/><rect x="9" y="3" width="3" height="10" rx="1" fill="currentColor"/></svg>
                  On Hold
                </button>
              {:else}
                <button on:click={(e) => quickSetStatus(e, project.id, 'active')}>
                  <svg viewBox="0 0 16 16" class="menu-icon"><polygon points="4,2 14,8 4,14" fill="currentColor"/></svg>
                  Reactivate
                </button>
              {/if}
              {#if project.status !== 'deprecated'}
                <button class="danger-action" on:click={(e) => quickSetStatus(e, project.id, 'deprecated')}>
                  <svg viewBox="0 0 16 16" class="menu-icon"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5" fill="none"/><line x1="4" y1="4" x2="12" y2="12" stroke="currentColor" stroke-width="1.5"/></svg>
                  Deprecated
                </button>
              {:else}
                <button on:click={(e) => quickSetStatus(e, project.id, 'active')}>
                  <svg viewBox="0 0 16 16" class="menu-icon"><polygon points="4,2 14,8 4,14" fill="currentColor"/></svg>
                  Reactivate
                </button>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>

    {#if $projects.length === 0 && $areas.length === 0}
      <p class="empty">{t('noProjects', $language)}</p>
    {/if}
  </nav>

  <div class="sidebar-footer">
    <label class="toggle-label">
      <input type="checkbox" bind:checked={showArchived} on:change={doSearch} />
      {t('archived', $language)}
    </label>
  </div>
</aside>
{:else}
  <button class="sidebar-toggle" on:click={() => sidebarOpen.set(true)}>☰</button>
{/if}

<style>
  .sidebar {
    width: var(--sidebar-width);
    min-width: var(--sidebar-width);
    height: 100vh;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 1rem;
    gap: 0.75rem;
    overflow-y: auto;
  }
  .sidebar-header { display: flex; justify-content: space-between; align-items: center; }
  .sidebar-header h2 { font-size: 1.1rem; font-weight: 600; }
  .sidebar-controls { display: flex; gap: 0.25rem; }
  .sidebar-controls select { flex: 1; font-size: 0.75rem; padding: 0.3rem; }
  .sidebar-actions { display: flex; gap: 0.5rem; }
  .small { font-size: 0.75rem; padding: 0.3rem 0.6rem; }
  .icon-btn { background: none; border: none; font-size: 1.1rem; padding: 0.25rem; color: var(--text-secondary); cursor: pointer; }

  .inline-form { display: flex; flex-direction: column; gap: 0.4rem; padding: 0.5rem; background: var(--bg); border-radius: var(--radius); }
  .inline-actions { display: flex; gap: 0.25rem; }
  .project-tree { flex: 1; overflow-y: auto; }

  .tree-group { margin-bottom: 0.25rem; border-radius: var(--radius); transition: background 0.15s; }
  .tree-group.drop-target { outline: 2px dashed var(--accent); outline-offset: -2px; }
  .tree-group-header { display: flex; align-items: center; gap: 0.25rem; padding: 0.3rem 0.25rem; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); font-weight: 600; }
  .folder-toggle { background: none; border: none; padding: 0; font-size: 0.6rem; color: var(--text-muted); cursor: pointer; width: 14px; text-align: center; }
  .folder-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .folder-count { font-size: 0.65rem; background: var(--bg-tertiary); padding: 0 0.35rem; border-radius: 8px; color: var(--text-muted); }
  .folder-actions { display: flex; gap: 0; opacity: 0; transition: opacity 0.15s; }
  .tree-group-header:hover .folder-actions { opacity: 1; }
  .folder-btn { background: none; border: none; font-size: 0.8rem; padding: 0 0.2rem; color: var(--text-muted); cursor: pointer; }
  .folder-btn:hover { color: var(--accent); }
  .folder-btn.danger:hover { color: var(--danger); }
  .rename-input { flex: 1; font-size: 0.75rem; padding: 0.15rem 0.3rem; border: 1px solid var(--accent); border-radius: 3px; background: var(--bg); color: var(--text); }

  /* Project items */
  .tree-item-row { position: relative; display: flex; align-items: center; }
  .tree-item {
    display: flex; align-items: center; gap: 0.3rem; flex: 1;
    text-align: left; padding: 0.35rem 0.5rem 0.35rem 1.2rem;
    border: none; background: none; border-radius: var(--radius);
    color: var(--text); font-size: 0.85rem; cursor: pointer;
  }
  .tree-item:hover { background: var(--bg-tertiary); }
  .tree-item.dimmed { opacity: 0.5; }
  .tree-item[draggable="true"] { cursor: grab; }
  .tree-item[draggable="true"]:active { cursor: grabbing; opacity: 0.6; }
  .drag-handle { font-size: 0.7rem; color: var(--text-muted); opacity: 0; transition: opacity 0.15s; user-select: none; }
  .tree-item:hover .drag-handle { opacity: 0.6; }
  .status-icon { font-size: 0.7rem; flex-shrink: 0; }
  .project-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mini-tags { display: flex; gap: 0.15rem; flex-shrink: 0; }
  .mini-tag { font-size: 0.55rem; padding: 0 0.25rem; background: var(--bg-tertiary); border-radius: 3px; color: var(--text-muted); white-space: nowrap; }
  .mini-stars { color: #f5a623; font-size: 0.6rem; }

  .tag-filter { display: flex; gap: 0.25rem; align-items: center; }
  .tag-filter select { flex: 1; font-size: 0.75rem; padding: 0.3rem; }
  .tag-clear { background: none; border: none; font-size: 1rem; color: var(--text-muted); cursor: pointer; padding: 0 0.2rem; line-height: 1; }
  .tag-clear:hover { color: var(--danger); }

  /* Action trigger (⋯ button) */
  .action-trigger {
    background: none; border: none; color: var(--text-muted); font-size: 1rem;
    padding: 0 0.3rem; cursor: pointer; opacity: 0; transition: opacity 0.15s;
    line-height: 1; flex-shrink: 0;
  }
  .tree-item-row:hover .action-trigger { opacity: 1; }
  .action-trigger:hover { color: var(--text); }

  /* Dropdown action menu */
  .action-menu {
    position: absolute; right: 0; top: 100%; z-index: 50;
    background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius);
    box-shadow: 0 4px 16px var(--shadow); min-width: 150px; padding: 0.25rem 0;
  }
  .action-menu button {
    display: flex; align-items: center; gap: 0.4rem; width: 100%;
    text-align: left; padding: 0.4rem 0.75rem; border: none; background: none;
    font-size: 0.8rem; color: var(--text); cursor: pointer;
  }
  .action-menu button:hover { background: var(--bg-tertiary); }
  .action-menu .danger-action { color: var(--danger); }
  .action-menu .danger-action:hover { background: #fff0f0; }
  .menu-icon { width: 14px; height: 14px; flex-shrink: 0; }

  .empty { text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 2rem 0; }
  .empty-folder { font-size: 0.7rem; color: var(--text-muted); padding: 0.3rem 1.2rem; font-style: italic; }
  .sidebar-footer { border-top: 1px solid var(--border); padding-top: 0.5rem; }
  .toggle-label { font-size: 0.8rem; color: var(--text-secondary); display: flex; align-items: center; gap: 0.4rem; cursor: pointer; }
  .sidebar-toggle { position: fixed; top: 0.5rem; left: 0.5rem; z-index: 100; background: var(--bg-secondary); border: 1px solid var(--border); font-size: 1.2rem; padding: 0.4rem 0.6rem; border-radius: var(--radius); }
</style>
