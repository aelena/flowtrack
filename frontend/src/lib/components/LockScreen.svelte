<script>
  // The prompt shown before the interface. Verification is a round trip to the
  // API, so the hash never reaches the browser and there is nothing in the page
  // to compare against.
  //
  // Be clear about what this is. Every API route is behind the API key, which
  // the MCP server, the browser extension and the launcher all hold, so this
  // stops somebody sitting down at an unlocked machine. It does not stop anybody
  // who can read the API key. See backend/app/passwords.py.
  import { onMount } from 'svelte';
  import { verifyLock } from '$lib/api.js';
  import { unlocked, language } from '$lib/stores.js';
  import { t } from '$lib/i18n.js';

  let password = '';
  let error = '';
  let busy = false;
  let input;

  onMount(() => input?.focus());

  async function submit() {
    if (busy || !password) return;
    busy = true;
    error = '';
    try {
      await verifyLock(password);
      password = '';
      unlocked.set(true);
    } catch {
      // Deliberately one message for every failure. Distinguishing "wrong
      // password" from anything else tells whoever is trying which half to
      // change.
      error = t('lockWrong', $language);
      password = '';
      input?.focus();
    } finally {
      busy = false;
    }
  }
</script>

<div class="lock">
  <form class="panel" on:submit|preventDefault={submit}>
    <h1>{t('lockTitle', $language)}</h1>
    <p class="prompt">{t('lockPrompt', $language)}</p>

    <!-- svelte-ignore a11y-autofocus -->
    <input
      bind:this={input}
      bind:value={password}
      type="password"
      autocomplete="current-password"
      aria-label={t('lockPrompt', $language)}
      aria-invalid={error ? 'true' : 'false'}
      disabled={busy}
    />

    <!-- Always rendered, so the panel does not jump when a message appears. -->
    <p class="error" role="alert" aria-live="polite">{error}</p>

    <button type="submit" disabled={busy || !password}>
      {t('lockUnlock', $language)}
    </button>
  </form>
</div>

<style>
  .lock {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg);
  }

  .panel {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    width: min(22rem, calc(100vw - 2rem));
    padding: 1.75rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-secondary);
  }

  h1 {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text);
  }

  .prompt {
    margin: 0 0 0.5rem 0;
    font-size: 0.8rem;
    color: var(--text-secondary);
  }

  input {
    width: 100%;
  }

  .error {
    margin: 0;
    min-height: 1.1rem;
    font-size: 0.75rem;
    color: var(--danger, #c0392b);
  }

  button {
    padding: 0.45rem 0.8rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg);
    color: var(--text);
    font-weight: 500;
  }

  button:hover:not(:disabled) {
    border-color: var(--accent);
  }

  button:disabled {
    opacity: 0.55;
  }
</style>
