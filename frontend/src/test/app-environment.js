// Stub for $app/environment under vitest. happy-dom gives us a window and a
// localStorage, so the persisted stores should behave as they do in a browser.
export const browser = true;
export const dev = true;
export const building = false;
export const version = 'test';
