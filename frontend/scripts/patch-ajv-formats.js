#!/usr/bin/env node
/**
 * Postinstall patches so craco start works (Node 24 + eslint defaultMeta crash).
 * 1) ajv-keywords: guard when ajv._formats is undefined.
 * 2) react-scripts: force-disable ESLint webpack plugin (no defaultMeta crash).
 */
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');

// --- Patch 1: fork-ts-checker ajv-keywords ---
const ajvFile = path.join(
  root,
  'node_modules',
  'fork-ts-checker-webpack-plugin',
  'node_modules',
  'ajv-keywords',
  'keywords',
  '_formatLimit.js'
);
if (fs.existsSync(ajvFile)) {
  let content = fs.readFileSync(ajvFile, 'utf8');
  if (!content.includes('if (!formats) return;')) {
    content = content.replace(
      '  var formats = ajv._formats;\n  for (var name in COMPARE_FORMATS)',
      '  var formats = ajv._formats;\n  if (!formats) return;\n  for (var name in COMPARE_FORMATS)'
    );
    fs.writeFileSync(ajvFile, content);
  }
}

// --- Patch 2: react-scripts — force disable ESLint plugin in webpack config ---
const webpackConfigPath = path.join(root, 'node_modules', 'react-scripts', 'config', 'webpack.config.js');
if (fs.existsSync(webpackConfigPath)) {
  let content = fs.readFileSync(webpackConfigPath, 'utf8');
  content = content.replace(
    "const disableESLintPlugin = process.env.DISABLE_ESLINT_PLUGIN === 'true';",
    "const disableESLintPlugin = true; // patched"
  );
  content = content.replace(/!disableESLintPlugin\s*&&\s*new ESLintPlugin\(/g, 'false && new ESLintPlugin(');
  fs.writeFileSync(webpackConfigPath, content);
}

// --- Patch 3: eslint-webpack-plugin → no-op (fixes defaultMeta in main + child compilation) ---
const eslintPluginPath = path.join(root, 'node_modules', 'eslint-webpack-plugin', 'dist', 'index.js');
if (fs.existsSync(eslintPluginPath)) {
  const noop = `"use strict";
// Replaced by postinstall to avoid "Cannot set properties of undefined (setting 'defaultMeta')"
class ESLintWebpackPlugin {
  constructor() {}
  apply() {}
}
module.exports = ESLintWebpackPlugin;
`;
  fs.writeFileSync(eslintPluginPath, noop);
}

// --- Patch 4: craco eslint.js — when enable is false, skip getPlugin (avoids "Cannot find ESLint plugin" warning) ---
const cracoEslintPath = path.join(root, 'node_modules', '@craco', 'craco', 'dist', 'lib', 'features', 'webpack', 'eslint.js');
if (fs.existsSync(cracoEslintPath)) {
  let content = fs.readFileSync(cracoEslintPath, 'utf8');
  if (!content.includes('patched: check enable first')) {
    // Also silence "Couldn't disabled ESLint" when plugin isn't in config (react-scripts patched)
    content = content.replace(
      '    else {\n        (0, logger_1.logError)("Couldn\'t disabled ESLint.");\n    }',
      '    else { /* plugin not in config (expected when react-scripts patched) */ }'
    );
    const oldBlock = `    if (cracoConfig.eslint) {
        var _a = (0, webpack_plugins_1.getPlugin)(webpackConfig, (0, webpack_plugins_1.pluginByName)('ESLintWebpackPlugin')), isFound = _a.isFound, match = _a.match;
        if (!isFound) {
            (0, logger_1.logError)('Cannot find ESLint plugin (ESLintWebpackPlugin).');
            return webpackConfig;
        }
        var _b = cracoConfig.eslint, enable = _b.enable, mode = _b.mode, pluginOptions = _b.pluginOptions;
        if (enable === false) {
            disableEslint(webpackConfig);
            return webpackConfig;
        }
`;
    const newBlock = `    if (cracoConfig.eslint) {
        var _b = cracoConfig.eslint, enable = _b.enable, mode = _b.mode, pluginOptions = _b.pluginOptions;
        if (enable === false) {
            disableEslint(webpackConfig);
            return webpackConfig;
        }
        var _a = (0, webpack_plugins_1.getPlugin)(webpackConfig, (0, webpack_plugins_1.pluginByName)('ESLintWebpackPlugin')), isFound = _a.isFound, match = _a.match;
        if (!isFound) {
            (0, logger_1.logError)('Cannot find ESLint plugin (ESLintWebpackPlugin).');
            return webpackConfig;
        }
`;
    if (content.includes(oldBlock.split('\n')[1])) {
      content = content.replace(oldBlock, newBlock);
      fs.writeFileSync(cracoEslintPath, content);
    }
  }
}

process.exit(0);
