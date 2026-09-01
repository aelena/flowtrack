import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  test: {
    environment: 'happy-dom',
    include: ['src/**/*.test.js'],
    // The default is 5s. Three of the store tests call vi.resetModules() and
    // re-import stores.js to check what it reads at import time, which is a full
    // transform and evaluate each time. On a warm machine that is about a second;
    // on the first run in a cold container it went over five and those three
    // failed, then three consecutive runs after it passed. A timeout that only
    // trips on a cold cache reports the machine, not the code.
    testTimeout: 20000,
    // stores.js imports `browser` from $app/environment, which only resolves
    // inside a SvelteKit build. Point it at a stub for unit tests.
    alias: {
      '$app/environment': new URL('./src/test/app-environment.js', import.meta.url).pathname,
    },
  },
});
