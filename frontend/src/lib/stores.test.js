import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// stores.js reads localStorage at import time, so each test that cares about
// the hydrated value has to reset the module registry and re-import.
async function freshStores() {
  vi.resetModules();
  return import('./stores.js');
}

describe('persisted preferences', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it('falls back to the default when nothing is stored', async () => {
    const { theme } = await freshStores();
    expect(get(theme)).toBe('light');
  });

  it('hydrates from localStorage', async () => {
    localStorage.setItem('flowtrack:theme', JSON.stringify('dark'));
    const { theme } = await freshStores();
    expect(get(theme)).toBe('dark');
  });

  it('writes back on change, under a namespaced key', async () => {
    const { theme } = await freshStores();
    theme.set('dark');
    expect(localStorage.getItem('flowtrack:theme')).toBe(JSON.stringify('dark'));
  });

  it('survives a corrupt stored value instead of throwing', async () => {
    localStorage.setItem('flowtrack:language', 'not json');
    const { language } = await freshStores();
    expect(get(language)).toBe('en');
  });

  it('survives storage being unavailable', async () => {
    // Private browsing and exhausted quota both throw on setItem. A failure to
    // persist a preference must never break the app.
    const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
    const { font } = await freshStores();
    expect(() => font.set('Georgia')).not.toThrow();
    expect(get(font)).toBe('Georgia');
    setItem.mockRestore();
  });

  it('persists booleans, not just strings', async () => {
    const { sidebarOpen } = await freshStores();
    expect(get(sidebarOpen)).toBe(true);
    sidebarOpen.set(false);
    expect(localStorage.getItem('flowtrack:sidebarOpen')).toBe('false');
  });
});

describe('toasts', () => {
  it('adds a toast and removes it when its time is up', async () => {
    vi.useFakeTimers();
    const { toasts, showToast } = await freshStores();

    showToast('something broke', 'error', 1000);
    expect(get(toasts)).toHaveLength(1);
    expect(get(toasts)[0].message).toBe('something broke');

    vi.advanceTimersByTime(1001);
    expect(get(toasts)).toHaveLength(0);

    vi.useRealTimers();
  });
});
