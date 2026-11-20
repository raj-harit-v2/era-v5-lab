module.exports = {
  rootDir: '/work/run',
  testEnvironment: 'node',
  transform: { '\\.[jt]s$': ['babel-jest', { configFile: '/work/babel.config.cjs' }] },
  moduleFileExtensions: ['js', 'ts', 'json'],
  testMatch: ['**/*.spec.js', '**/*.test.ts'],
  modulePaths: ['/work/node_modules'],
  cache: false,
};
