import { describe, expect, it } from 'vitest';

import { daysSince, shortDate, tsFilename } from './utils.js';

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

describe('shortDate', () => {
  it('formats an ISO timestamp as a sortable calendar date', () => {
    expect(shortDate('2026-08-24T12:55:00Z')).toMatch(/^2026-08-\d{2}$/);
  });

  it('zero-pads month and day', () => {
    expect(shortDate('2026-01-05T10:00:00')).toBe('2026-01-05');
  });

  it('returns an empty string rather than "Invalid Date"', () => {
    expect(shortDate(null)).toBe('');
    expect(shortDate('')).toBe('');
    expect(shortDate('not a date')).toBe('');
  });
});

describe('daysSince', () => {
  const now = new Date('2026-08-24T09:00:00');

  it('counts today as zero', () => {
    expect(daysSince('2026-08-24T01:00:00', now)).toBe(0);
  });

  it('counts calendar days, not elapsed hours', () => {
    // Nine hours earlier, but the day before: a reader calls that one day old.
    expect(daysSince('2026-08-23T23:50:00', now)).toBe(1);
  });

  it('handles longer gaps', () => {
    expect(daysSince('2026-08-17T19:32:00', now)).toBe(7);
  });

  it('returns null for anything unparseable, so callers can branch', () => {
    expect(daysSince(null, now)).toBeNull();
    expect(daysSince('nope', now)).toBeNull();
  });
});
