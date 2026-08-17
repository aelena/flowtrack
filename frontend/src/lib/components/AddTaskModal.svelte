<script>
  import { createEventDispatcher } from 'svelte';
  import { createTasks } from '../api.js';
  import { showToast } from '../stores.js';

  export let projectId;

  const dispatch = createEventDispatcher();
  let content = '';
  let description = '';

  async function handleSubmit() {
    if (!content.trim()) return;
    try {
      await createTasks(projectId, content, description || null);
      dispatch('close');
    } catch (e) {
      showToast(e.message);
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') dispatch('close');
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="modal-overlay" role="presentation" on:click|self={() => dispatch('close')}>
  <div class="modal">
    <h3>Add Tasks</h3>
    <p class="hint">
      Type a single task, or paste a bullet/ordered list to create multiple tasks at once.
    </p>

    <textarea
      bind:value={content}
      placeholder="- Design the homepage&#10;- Build the API&#10;- Write tests"
      rows="6"
    ></textarea>

    <input type="text" bind:value={description} placeholder="Optional description for all tasks" />

    <div class="modal-actions">
      <button class="primary" on:click={handleSubmit}>Create</button>
      <button on:click={() => dispatch('close')}>Cancel</button>
    </div>
  </div>
</div>

<style>
  .hint {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 0.75rem;
  }

  textarea {
    font-family: var(--font-mono);
    font-size: 0.85rem;
  }

  input {
    margin-top: 0.5rem;
  }

  .modal-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
    justify-content: flex-end;
  }
</style>
