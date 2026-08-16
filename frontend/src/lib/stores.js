import { writable } from 'svelte/store';

export const projects = writable([]);
export const currentProject = writable(null);
export const areas = writable([]);
export const theme = writable('light');
export const language = writable('en');
export const font = writable('Segoe UI');
export const sidebarOpen = writable(true);
export const apiKey = writable('ft_dev_key_change_me');

export const toasts = writable([]);

let toastId = 0;

export function showToast(message, type = 'error', duration = 4000) {
  const id = ++toastId;
  toasts.update(t => [...t, { id, message, type }]);
  setTimeout(() => {
    toasts.update(t => t.filter(x => x.id !== id));
  }, duration);
}
