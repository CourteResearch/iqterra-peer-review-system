import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['pkg/**/*.test.ts'],
  },
});
