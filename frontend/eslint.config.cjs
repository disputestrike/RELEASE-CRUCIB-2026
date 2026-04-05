"use strict";

const js = require("@eslint/js");
const react = require("eslint-plugin-react");
const reactHooks = require("eslint-plugin-react-hooks");
const globals = require("globals");

/** ESLint 9 flat config — CRA/craco (webpack ESLint plugin disabled). */
module.exports = [
  { ignores: ["build/**", "node_modules/**", "coverage/**", "public/**"] },
  js.configs.recommended,
  react.configs.flat.recommended,
  {
    files: ["src/**/*.{js,jsx}"],
    plugins: { "react-hooks": reactHooks },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off",
      "no-unused-vars": [
        "warn",
        { varsIgnorePattern: "^_", argsIgnorePattern: "^_", caughtErrors: "none" },
      ],
    },
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.jest,
        React: "readonly",
      },
    },
    settings: { react: { version: "detect" } },
    linterOptions: {
      reportUnusedDisableDirectives: "off",
    },
  },
  {
    files: ["src/**/*.{js,jsx}"],
    rules: {
      "no-empty": "warn",
      "no-useless-escape": "warn",
      "react/display-name": "warn",
      "react/no-unescaped-entities": "off",
      "react/no-unknown-property": "off",
      "no-constant-binary-expression": "off",
    },
  },
  // Large page modules: enforce hooks/vars in components; burn these down over time.
  {
    files: ["src/pages/**/*.{js,jsx}"],
    rules: {
      "no-unused-vars": "off",
      "react-hooks/exhaustive-deps": "off",
    },
  },
];
