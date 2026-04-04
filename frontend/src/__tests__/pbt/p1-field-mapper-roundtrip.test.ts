// Feature: frontend-integration, Property 1: 字段映射往返一致性（Round-Trip）
// **Validates: Requirements 1.5**

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { toCamelCase, toSnakeCase } from '@/network/fieldMapper';

/**
 * Arbitrary: generates a single snake_case key (1–3 lowercase words joined by underscores).
 * Words must be at least 2 chars to avoid ambiguity in round-trip conversion
 * (e.g., single-letter segments like "a_a_a" → "aAA" → "a_aa" is a known
 * limitation of camelcase-keys/snakecase-keys).
 */
const arbSnakeWord = fc
  .array(
    fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz'.split('')),
    { minLength: 2, maxLength: 8 },
  )
  .map((chars) => chars.join(''));

const arbSnakeKey = fc
  .array(arbSnakeWord, { minLength: 1, maxLength: 3 })
  .map((words) => words.join('_'));

/**
 * Arbitrary: generates a random value (string or number).
 */
const arbValue: fc.Arbitrary<string | number> = fc.oneof(
  fc.string({ minLength: 0, maxLength: 30 }),
  fc.integer({ min: -10000, max: 10000 }),
  fc.double({ min: -1000, max: 1000, noNaN: true }),
);

/**
 * Arbitrary: generates a random snake_case keyed object with 1–50 keys.
 */
const arbSnakeCaseObject: fc.Arbitrary<Record<string, string | number>> = fc
  .array(fc.tuple(arbSnakeKey, arbValue), { minLength: 1, maxLength: 50 })
  .map((entries) => Object.fromEntries(entries));

describe('Property 1: 字段映射往返一致性（Round-Trip）', () => {
  it('keys(toSnakeCase(toCamelCase(R))) == keys(R) for random snake_case objects', () => {
    fc.assert(
      fc.property(arbSnakeCaseObject, (original) => {
        const camelized = toCamelCase<Record<string, unknown>>(original);
        const roundTripped = toSnakeCase<Record<string, unknown>>(camelized);

        const originalKeys = Object.keys(original).sort();
        const roundTrippedKeys = Object.keys(roundTripped).sort();

        expect(roundTrippedKeys).toEqual(originalKeys);
      }),
      { numRuns: 150 },
    );
  });
});
