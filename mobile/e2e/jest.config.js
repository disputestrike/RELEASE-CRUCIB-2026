module.exports = {
  rootDir: '..',
  testMatch: ['<rootDir>/e2e/**/*.e2e.js'],
  testTimeout: 120000,
  maxWorkers: 1,
  reporters: ['default'],
  verbose: true,
  testEnvironment: process.env.DETOX_E2E === '1' ? 'detox/runners/jest/testEnvironment' : 'node',
};
