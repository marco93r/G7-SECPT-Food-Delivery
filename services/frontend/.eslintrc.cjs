module.exports = {
  root: true,
  env: {
    browser: true,
    es2020: true,
  },
  extends: [
    "eslint:recommended",
    "plugin:react-hooks/recommended",
  ],
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
  },
  settings: {
    react: {
      version: "detect",
    },
  },
  rules: {
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "warn",
  },
  ignorePatterns: ["dist", "node_modules"],
};
