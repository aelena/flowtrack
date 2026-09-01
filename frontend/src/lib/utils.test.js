import { describe, expect, it } from 'vitest';

import { daysSince, projectHealth, shortDate, tsFilename } from './utils.js';

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

describe('projectHealth', () => {
  const NOW = new Date('2026-09-01T12:00:00Z');
  const iso = (daysAgo) => new Date(NOW.getTime() - daysAgo * 86400000).toISOString();
  const date = (daysFromNow) =>
    new Date(NOW.getTime() + daysFromNow * 86400000).toISOString().slice(0, 10);

  const active = (over = {}) => ({
    status: 'active',
    archived: false,
    task_completion: 40,
    last_activity_at: iso(1),
    desired_end_date: null,
    ...over,
  });

  it('is green for something touched recently', () => {
    expect(projectHealth(active(), NOW).level).toBe('good');
  });

  // The point of grey. Eight projects are on hold on purpose, and a deliberate
  // freeze painted red is how the column stops being read.
  it.each(['on_hold', 'deprecated'])('is grey for status %s, whatever its dates', (status) => {
    const p = active({ status, last_activity_at: iso(400), desired_end_date: date(-100) });
    expect(projectHealth(p, NOW).level).toBe('frozen');
  });

  it('is grey when archived', () => {
    expect(projectHealth(active({ archived: true }), NOW).level).toBe('frozen');
  });

  it('is red past the target date when unfinished', () => {
    const p = active({ desired_end_date: date(-3) });
    const health = projectHealth(p, NOW);
    expect(health.level).toBe('bad');
    expect(health.reason).toContain('3 days past');
  });

  it('is not red past the target date once finished', () => {
    const p = active({ desired_end_date: date(-3), task_completion: 100 });
    expect(projectHealth(p, NOW).level).toBe('good');
  });

  it('is red after a long silence', () => {
    const p = active({ last_activity_at: iso(90) });
    const health = projectHealth(p, NOW);
    expect(health.level).toBe('bad');
    expect(health.reason).toContain('90 days');
  });

  it('is amber when the target date is close', () => {
    const p = active({ desired_end_date: date(5) });
    expect(projectHealth(p, NOW).level).toBe('warn');
  });

  it('is amber after a moderate silence', () => {
    expect(projectHealth(active({ last_activity_at: iso(30) }), NOW).level).toBe('warn');
  });

  it('prefers the overdue reason to the stale one', () => {
    // Both apply. The date is a fact and the silence is a heuristic, so the
    // fact should be what the reader is told.
    const p = active({ desired_end_date: date(-10), last_activity_at: iso(200) });
    expect(projectHealth(p, NOW).reason).toContain('past its target date');
  });

  it('says so rather than guessing when there is no activity at all', () => {
    const p = active({ last_activity_at: null });
    expect(projectHealth(p, NOW).level).toBe('unknown');
  });

  it('survives being handed nothing', () => {
    expect(projectHealth(null).level).toBe('unknown');
    expect(projectHealth(undefined).level).toBe('unknown');
  });

  it('always returns a reason to show', () => {
    for (const p of [
      active(),
      active({ status: 'on_hold' }),
      active({ desired_end_date: date(-1) }),
      active({ last_activity_at: iso(90) }),
      active({ desired_end_date: date(2) }),
      active({ last_activity_at: iso(30) }),
    ]) {
      expect(projectHealth(p, NOW).reason).not.toBe('');
    }
  });
});
