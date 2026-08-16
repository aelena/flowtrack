import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  test: {
    environment: 'happy-dom',
    include: ['src/**/*.test.js'],
    // stores.js imports `browser` from $app/environment, which only resolves
    // inside a SvelteKit build. Point it at a stub for unit tests.
    alias: {
      '$app/environment': new URL('./src/test/app-environment.js', import.meta.url).pathname,
    },
  },
});
