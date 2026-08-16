<script>
  import { toasts } from '../stores.js';
</script>

{#if $toasts.length > 0}
  <div class="toast-container">
    {#each $toasts as toast (toast.id)}
      <div class="toast {toast.type}">
        <span class="toast-icon">
          {#if toast.type === 'error'}!{:else if toast.type === 'success'}&check;{:else}i{/if}
        </span>
        <span class="toast-msg">{toast.message}</span>
      </div>
    {/each}
  </div>
{/if}

<style>
  .toast-container {
    position: fixed;
    bottom: 1.5rem;
    right: 1.5rem;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    max-width: 400px;
  }

  .toast {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.65rem 1rem;
    border-radius: var(--radius);
    font-size: 0.82rem;
    line-height: 1.4;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.18);
    animation: slide-in 0.25s ease-out;
  }

  .toast.error {
    background: #fdecea;
    color: #611a15;
    border-left: 3px solid var(--danger);
  }

  .toast.success {
    background: #e8f5e9;
    color: #1b5e20;
    border-left: 3px solid var(--success);
  }

  .toast.info {
    background: #e3f2fd;
    color: #0d47a1;
    border-left: 3px solid var(--info);
  }

  :global([data-theme="dark"]) .toast.error {
    background: #3b1414;
    color: #f8b4b4;
  }

  :global([data-theme="dark"]) .toast.success {
    background: #14301a;
    color: #a5d6a7;
  }

  :global([data-theme="dark"]) .toast.info {
    background: #0d1b2a;
    color: #90caf9;
  }

  .toast-icon {
    font-weight: 700;
    font-size: 0.85rem;
    flex-shrink: 0;
    width: 16px;
    text-align: center;
  }

  .toast-msg {
    flex: 1;
    word-break: break-word;
  }

  @keyframes slide-in {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
