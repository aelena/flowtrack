import { describe, expect, it } from 'vitest';

import { tsFilename } from './utils.js';

describe('tsFilename', () => {
  it('slugifies whitespace so the download name is not broken', () => {
    expect(tsFilename('My Project', 'zip')).toMatch(/^My_Project-\d{8}-\d{6}\.zip$/);
  });

  it('falls back to "project" when there is no name', () => {
    expect(tsFilename('', 'json')).toMatch(/^project-/);
    expect(tsFilename(null, 'json')).toMatch(/^project-/);
  });

  it('zero-pads every component of the stamp', () => {
    // A missing pad would produce names that neither sort nor parse.
    const name = tsFilename('x', 'json');
    const stamp = name.slice('x-'.length, -'.json'.length);
    expect(stamp).toHaveLength(15); // YYYYMMDD-HHMMSS
  });
});
