import { writable } from 'svelte/store';
import { browser } from '$app/environment';

const STORAGE_PREFIX = 'flowtrack:';

/**
 * A writable store backed by localStorage.
 *
 * Falls back to the in-memory default when storage is unavailable (SSR,
 * private browsing, quota exhausted) so a failure to persist never breaks
 * the app — it only means the preference does not survive a reload.
 */
function persisted(key, initial) {
  const storageKey = STORAGE_PREFIX + key;
  let start = initial;

  if (browser) {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw !== null) start = JSON.parse(raw);
    } catch {
      // Unreadable or corrupt value: keep the default.
    }
  }

  const store = writable(start);

  if (browser) {
    store.subscribe((value) => {
      try {
        localStorage.setItem(storageKey, JSON.stringify(value));
      } catch {
        // Storage full or blocked: the preference just will not persist.
      }
    });
  }

  return store;
}

export const projects = writable([]);
export const currentProject = writable(null);
export const areas = writable([]);

// User preferences — persisted across reloads.
export const theme = persisted('theme', 'light');
export const language = persisted('language', 'en');
export const font = persisted('font', 'Segoe UI');
export const sidebarOpen = persisted('sidebarOpen', true);
export const apiKey = persisted('apiKey', 'ft_dev_key_change_me');
// The host-side launcher. Empty disables the feature entirely, and the note
// buttons fall back to putting the command on the clipboard.
export const launcherUrl = persisted('launcherUrl', 'http://localhost:7030');

export const toasts = writable([]);

let toastId = 0;

export function showToast(message, type = 'error', duration = 4000) {
  const id = ++toastId;
  toasts.update((t) => [...t, { id, message, type }]);
  setTimeout(() => {
    toasts.update((t) => t.filter((x) => x.id !== id));
  }, duration);
}
