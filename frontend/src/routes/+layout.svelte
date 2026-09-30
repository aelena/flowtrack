<script>
  import '../app.css';
  import { theme, language, font, sidebarOpen, unlocked } from '$lib/stores.js';
  import Sidebar from '$lib/components/Sidebar.svelte';
  import Toast from '$lib/components/Toast.svelte';
  import LockScreen from '$lib/components/LockScreen.svelte';
  import { getLock } from '$lib/api.js';
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { t } from '$lib/i18n.js';

  // 'checking' until the API has answered. The app must not render first and
  // lock a moment later: a dashboard visible for two hundred milliseconds is a
  // dashboard that was read.
  let gate = 'checking';

  async function checkLock() {
    gate = 'checking';
    try {
      const { enabled, lock_on_open } = await getLock();
      gate = enabled && lock_on_open ? 'locked' : 'open';
    } catch {
      // The API did not answer, so whether this is locked is unknown. Staying
      // in 'checking' keeps the data off the screen; failing open would let an
      // API blip bypass the lock, and failing to a lock screen would ask for a
      // password nothing can verify.
      gate = 'unreachable';
    }
  }

  onMount(() => {
    checkLock();
    const unsubTheme = theme.subscribe((v) => {
      document.documentElement.setAttribute('data-theme', v);
    });
    const unsubFont = font.subscribe((v) => {
      document.documentElement.style.setProperty('--font-family', `'${v}', system-ui, sans-serif`);
    });
    return () => {
      unsubTheme();
      unsubFont();
    };
  });

  function toggleTheme() {
    theme.update((v) => (v === 'light' ? 'dark' : 'light'));
  }

  function toggleLang() {
    language.update((v) => (v === 'en' ? 'es' : 'en'));
  }
</script>

{#if gate === 'checking'}
  <div class="gate" aria-busy="true"></div>
{:else if gate === 'unreachable'}
  <div class="gate">
    <p>Cannot reach the API, so whether this is locked is unknown.</p>
    <button class="toggle-btn" on:click={checkLock}>Retry</button>
  </div>
{:else if gate === 'locked' && !$unlocked}
  <LockScreen />
{:else}
  <div class="app-layout">
    <Sidebar />

    <div class="main-area">
      <div class="toolbar">
        <div class="toolbar-left">
          {#if !$sidebarOpen}
            <button class="icon-btn" on:click={() => sidebarOpen.set(true)}>☰</button>
          {/if}
          <!-- Every other route was a dead end: the only way back to the
             portfolio view was the browser button or a sidebar entry. -->
          {#if $page.url.pathname !== '/'}
            <a
              href="/"
              class="icon-btn home-link"
              title={t('home', $language)}
              aria-label={t('home', $language)}
            >
              <svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true">
                <path fill="currentColor" d="M8 1.3 1 7.1v.9h1.9V14h3.6v-3.7h3V14h3.6V8h1.9v-.9z" />
              </svg>
            </a>
          {/if}
          <span class="brand">FlowTrack</span>
        </div>
        <div class="toolbar-right">
          <select class="font-select" value={$font} on:change={(e) => font.set(e.target.value)}>
            <option value="Segoe UI">Segoe UI</option>
            <option value="Georgia">Georgia</option>
            <option value="Consolas">Consolas</option>
            <option value="Arial">Arial</option>
            <option value="Palatino">Palatino</option>
          </select>

          <button class="toggle-btn" on:click={toggleLang}>
            {$language === 'en' ? 'ES' : 'EN'}
          </button>

          <button class="toggle-btn" on:click={toggleTheme}>
            {$theme === 'light' ? '☾ Dark' : '☀ Light'}
          </button>

          <a href="/settings" class="toggle-btn settings-link" title="Settings">
            <svg viewBox="0 0 16 16" width="14" height="14" style="vertical-align: middle;"
              ><path
                d="M8 10a2 2 0 100-4 2 2 0 000 4z"
                stroke="currentColor"
                fill="none"
                stroke-width="1.2"
              /><path
                d="M13.5 8c0-.3 0-.5-.1-.8l1.4-1.1-1.3-2.2-1.7.5c-.4-.3-.8-.6-1.3-.7L10 2H7.5l-.5 1.7c-.5.2-.9.4-1.3.7l-1.7-.5L2.7 6.1l1.4 1.1c-.1.3-.1.5-.1.8s0 .5.1.8L2.7 9.9 4 12.1l1.7-.5c.4.3.8.6 1.3.7L7.5 14H10l.5-1.7c.5-.2.9-.4 1.3-.7l1.7.5 1.3-2.2-1.4-1.1c.1-.3.1-.5.1-.8z"
                stroke="currentColor"
                fill="none"
                stroke-width="1.2"
              /></svg
            >
          </a>
        </div>
      </div>

      <main>
        <slot />
      </main>
    </div>
  </div>
{/if}

<Toast />

<style>
  .app-layout {
    display: flex;
    height: 100vh;
    overflow: hidden;
  }

  .gate {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    align-items: center;
    justify-content: center;
    height: 100vh;
    background: var(--bg);
    color: var(--text-secondary);
    font-size: 0.85rem;
  }

  .main-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 1rem;
    border-bottom: 1px solid var(--border);
    background: var(--bg-secondary);
    min-height: 44px;
  }

  .toolbar-left,
  .toolbar-right {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .brand {
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--text-secondary);
    letter-spacing: 0.02em;
  }

  .font-select {
    width: auto;
    font-size: 0.75rem;
    padding: 0.25rem 0.4rem;
  }

  .icon-btn {
    background: none;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.25rem 0.5rem;
    font-size: 1rem;
    color: var(--text-secondary);
  }

  .icon-btn:hover {
    background: var(--bg-tertiary);
  }

  /* .icon-btn was written for a button; as an anchor it needs the underline
     removed and the glyph centred on the line. */
  .home-link {
    display: inline-flex;
    align-items: center;
    text-decoration: none;
    line-height: 1;
  }

  .home-link:hover {
    color: var(--text);
    text-decoration: none;
  }

  .toggle-btn {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.3rem 0.6rem;
    font-size: 0.8rem;
    color: var(--text);
    font-weight: 500;
    white-space: nowrap;
  }

  .toggle-btn:hover {
    background: var(--bg-tertiary);
    border-color: var(--accent);
  }

  .settings-link {
    display: flex;
    align-items: center;
    text-decoration: none;
    color: var(--text);
    padding: 0.3rem 0.4rem;
  }

  main {
    flex: 1;
    overflow-y: auto;
    display: flex;
  }
</style>
