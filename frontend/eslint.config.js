import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import globals from 'globals';

export default [
  {
    ignores: ['build/', '.svelte-kit/', 'node_modules/', 'package-lock.json'],
  },
  js.configs.recommended,
  ...svelte.configs['flat/recommended'],
  {
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      // Deliberate no-ops in catch blocks are used where a failure to persist a
      // preference must not break the app; they carry an explanatory comment.
      'no-empty': ['error', { allowEmptyCatch: true }],
    },
  },
];
