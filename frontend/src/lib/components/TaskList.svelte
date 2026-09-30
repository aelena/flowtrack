<script>
  import { createEventDispatcher } from 'svelte';
  import { language, showToast, taskFilter } from '../stores.js';
  import { listTasks, updateTask, deleteTask } from '../api.js';
  import { t } from '../i18n.js';
  import { TASK_FILTERS, filterTasks, taskCounts } from '../utils.js';
  import AddTaskModal from './AddTaskModal.svelte';

  export let projectId;

  let tasks = [];
  let showAddModal = false;

  // The project's completion percentage is computed from these tasks but lives
  // on the parent, which has no other way of knowing a status just changed.
  const dispatch = createEventDispatcher();

  async function load() {
    if (!projectId) return;
    try {
      tasks = await listTasks(projectId);
    } catch (e) {
      showToast(e.message);
    }
  }

  async function cycleStatus(task) {
    const next = { new: 'in_progress', in_progress: 'done', done: 'new' };
    try {
      await updateTask(projectId, task.id, { status: next[task.status] });
      await load();
      dispatch('change');
    } catch (e) {
      showToast(e.message);
    }
  }

  async function removeTask(taskId) {
    try {
      await deleteTask(projectId, taskId);
      await load();
      dispatch('change');
    } catch (e) {
      showToast(e.message);
    }
  }

  $: (load(), projectId);

  // Filtered in the browser rather than re-fetched: the counts on the chips
  // need every task anyway. The API's ?status= filter is there for agents.
  $: counts = taskCounts(tasks);
  $: visible = filterTasks(tasks, $taskFilter);

  const FILTER_LABELS = {
    all: 'filterAll',
    new: 'pending',
    in_progress: 'inProgress',
    done: 'done',
  };
</script>

<div class="task-list">
  <div class="task-header">
    <h3>{t('tasks', $language)}</h3>
    <button class="primary small" on:click={() => (showAddModal = true)}
      >+ {t('newTask', $language)}</button
    >
  </div>

  {#if tasks.length === 0}
    <p class="empty">{t('noTasks', $language)}</p>
  {:else}
    <div class="task-filters" role="group" aria-label={t('filterTasks', $language)}>
      {#each TASK_FILTERS as filter}
        <button
          class="filter-chip"
          class:active={$taskFilter === filter}
          aria-pressed={$taskFilter === filter}
          on:click={() => taskFilter.set(filter)}
        >
          {t(FILTER_LABELS[filter], $language)}
          <span class="filter-count">{counts[filter]}</span>
        </button>
      {/each}
    </div>
    {#if visible.length === 0}
      <p class="empty">{t('noTasksMatch', $language)}</p>
    {/if}
    {#each visible as task (task.id)}
      <div class="task-item">
        <button class="status-btn badge {task.status}" on:click={() => cycleStatus(task)}>
          {task.status === 'new'
            ? t('pending', $language)
            : task.status === 'in_progress'
              ? t('inProgress', $language)
              : t('done', $language)}
        </button>
        <span class="task-title" class:done={task.status === 'done'}>{task.title}</span>
        <button class="icon-btn danger" on:click={() => removeTask(task.id)}>&#10005;</button>
      </div>
    {/each}
  {/if}
</div>

{#if showAddModal}
  <AddTaskModal
    {projectId}
    on:close={() => {
      showAddModal = false;
      load().then(() => dispatch('change'));
    }}
  />
{/if}

<style>
  .task-list {
    margin: 1rem 0;
  }

  .task-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }

  .task-header h3 {
    font-size: 1rem;
    font-weight: 600;
  }

  .small {
    font-size: 0.75rem;
    padding: 0.3rem 0.6rem;
  }

  .task-filters {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-bottom: 0.5rem;
  }

  .filter-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.6rem;
    font-size: 0.75rem;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: none;
    color: var(--text-secondary);
    cursor: pointer;
  }

  .filter-chip:hover {
    border-color: var(--accent);
    color: var(--accent);
  }

  .filter-chip.active {
    background: var(--accent);
    border-color: var(--accent);
    color: white;
    font-weight: 600;
  }

  .filter-count {
    font-size: 0.65rem;
    padding: 0 0.35rem;
    border-radius: 8px;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
  }

  .filter-chip.active .filter-count {
    background: rgb(255 255 255 / 25%);
    color: white;
  }

  .task-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem;
    border-bottom: 1px solid var(--border);
  }

  .task-item:last-child {
    border-bottom: none;
  }

  .status-btn {
    cursor: pointer;
    border: none;
    min-width: 80px;
    text-align: center;
  }

  .task-title {
    flex: 1;
    font-size: 0.9rem;
  }

  .task-title.done {
    text-decoration: line-through;
    color: var(--text-muted);
  }

  .icon-btn {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 0.8rem;
    padding: 0.2rem;
  }

  .icon-btn.danger:hover {
    color: var(--danger);
  }

  .empty {
    color: var(--text-muted);
    font-size: 0.85rem;
    text-align: center;
    padding: 1rem;
  }
</style>
