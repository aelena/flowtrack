<script>
  import { language, showToast } from '../stores.js';
  import { listTasks, updateTask, deleteTask } from '../api.js';
  import { t } from '../i18n.js';
  import AddTaskModal from './AddTaskModal.svelte';

  export let projectId;

  let tasks = [];
  let showAddModal = false;

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
    } catch (e) {
      showToast(e.message);
    }
  }

  async function removeTask(taskId) {
    try {
      await deleteTask(projectId, taskId);
      await load();
    } catch (e) {
      showToast(e.message);
    }
  }

  $: (load(), projectId);
</script>

<div class="task-list">
  <div class="task-header">
    <h3>{t('tasks', $language)}</h3>
    <button class="primary small" on:click={() => (showAddModal = true)}
      >+ {t('newTask', $language)}</button
    >
  </div>

  {#if tasks.length === 0}
    <p class="empty">No tasks yet</p>
  {:else}
    {#each tasks as task}
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
      load();
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
