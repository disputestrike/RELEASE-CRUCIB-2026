// craco.config.js
process.env.DISABLE_ESLINT_PLUGIN = "true";

const path = require("path");
require("dotenv").config();

const config = {
  enableHealthCheck: process.env.ENABLE_HEALTH_CHECK === "true",
  enableVisualEdits: false,
};

let setupDevServer;
if (config.enableVisualEdits) {
  setupDevServer = require("./plugins/visual-edits/dev-server-setup");
}

let WebpackHealthPlugin;
let setupHealthEndpoints;
let healthPluginInstance;

if (config.enableHealthCheck) {
  WebpackHealthPlugin = require("./plugins/health-check/webpack-health-plugin");
  setupHealthEndpoints = require("./plugins/health-check/health-endpoints");
  healthPluginInstance = new WebpackHealthPlugin();
}

const webpackConfig = {
  eslint: { enable: false },
  babel: {
    loaderOptions: (babelLoaderOptions) => {
      // In production, remove react-refresh plugin
      if (process.env.NODE_ENV === 'production') {
        if (babelLoaderOptions.plugins && Array.isArray(babelLoaderOptions.plugins)) {
          babelLoaderOptions.plugins = babelLoaderOptions.plugins.filter((plugin) => {
            if (!plugin) return false;
            const pluginName = Array.isArray(plugin) ? plugin[0] : plugin;
            if (typeof pluginName === 'string') {
              return !pluginName.includes('react-refresh');
            }
            return true;
          });
        }
      }
      return babelLoaderOptions;
    },
  },
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
    configure: (webpackConfig) => {
      if (Array.isArray(webpackConfig.plugins)) {
        webpackConfig.plugins = webpackConfig.plugins.filter((p) => {
          if (!p || !p.constructor) return true;
          const name = p.constructor.name || "";
          return name !== "ESLintWebpackPlugin" && !name.includes("ESLint");
        });
      }

      webpackConfig.watchOptions = {
        ...webpackConfig.watchOptions,
        ignored: [
          '**/node_modules/**',
          '**/.git/**',
          '**/build/**',
          '**/dist/**',
          '**/coverage/**',
          '**/public/**',
        ],
      };

      if (config.enableHealthCheck && healthPluginInstance) {
        webpackConfig.plugins.push(healthPluginInstance);
      }
      return webpackConfig;
    },
  },
};

webpackConfig.devServer = (devServerConfig) => {
  if (config.enableVisualEdits && setupDevServer) {
    devServerConfig = setupDevServer(devServerConfig);
  }

  if (config.enableHealthCheck && setupHealthEndpoints && healthPluginInstance) {
    const originalSetupMiddlewares = devServerConfig.setupMiddlewares;

    devServerConfig.setupMiddlewares = (middlewares, devServer) => {
      if (originalSetupMiddlewares) {
        middlewares = originalSetupMiddlewares(middlewares, devServer);
      }

      setupHealthEndpoints(devServer, healthPluginInstance);

      return middlewares;
    };
  }

  return devServerConfig;
};

module.exports = webpackConfig;
