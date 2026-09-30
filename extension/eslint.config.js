import js from "@eslint/js";
import globals from "globals";

export default [
  {
    ignores: ["node_modules/", "package-lock.json"],
  },
  js.configs.recommended,
  {
    files: ["background.js", "popup.js"],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: "script",
      globals: {
        ...globals.browser,
        // Without this, every chrome.* call reads as an undefined variable.
        // Worth being clear about the limit: this makes `chrome` known, so it
        // cannot catch a namespace that is missing at runtime because the
        // manifest did not request the permission. That was the actual bug
        // here, and only loading the extension finds it.
        ...globals.webextensions,
      },
    },
  },
  {
    files: ["eslint.config.js"],
    languageOptions: { ecmaVersion: 2023, sourceType: "module", globals: { ...globals.node } },
  },
];
