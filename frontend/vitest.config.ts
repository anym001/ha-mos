import { defineConfig } from 'vitest/config';

/**
 * Test setup for the card's pure logic.
 *
 * Deliberately node-only and DOM-free. What is worth testing here is device
 * selection, entity matching and name filtering — the part that implements the
 * documented `model_id` contract with the integration and has no Lit, no
 * `hass` and no rendering in it. Testing the component itself would need a DOM
 * shim and would mostly assert that Lit works, which it does.
 */
export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
  },
});
