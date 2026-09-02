import { describe, expect, it } from 'vitest';

import {
  clipPreview,
  daysSince,
  isInbox,
  projectHealth,
  safeExternalUrl,
  shortDate,
  tsFilename,
} from './utils.js';

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

describe('safeExternalUrl', () => {
  it('accepts http and https', () => {
    expect(safeExternalUrl('https://example.com/a?b=1')).toBe('https://example.com/a?b=1');
    expect(safeExternalUrl('http://example.com/')).toBe('http://example.com/');
  });

  // The clipper stores whatever the page reported, so these are the inputs that
  // matter: a link that executes when the user clicks it in the clip list.
  it('rejects script-bearing schemes', () => {
    expect(safeExternalUrl('javascript:alert(1)')).toBeNull();
    expect(safeExternalUrl('JaVaScRiPt:alert(1)')).toBeNull();
    expect(safeExternalUrl('data:text/html,<script>alert(1)</script>')).toBeNull();
    expect(safeExternalUrl('vbscript:msgbox(1)')).toBeNull();
    expect(safeExternalUrl('file:///etc/passwd')).toBeNull();
  });

  it('rejects empty, non-string and relative values', () => {
    expect(safeExternalUrl(null)).toBeNull();
    expect(safeExternalUrl('')).toBeNull();
    expect(safeExternalUrl('   ')).toBeNull();
    expect(safeExternalUrl(42)).toBeNull();
    expect(safeExternalUrl('/just/a/path')).toBeNull();
  });
});

describe('clipPreview', () => {
  it('collapses whitespace so a pasted block stays one line', () => {
    expect(clipPreview('an  idea\n\nworth   keeping')).toBe('an idea worth keeping');
  });

  it('truncates with an ellipsis past the limit', () => {
    const out = clipPreview('x'.repeat(300));
    expect(out).toHaveLength(241);
    expect(out.endsWith('…')).toBe(true);
  });

  it('leaves short content alone and tolerates non-strings', () => {
    expect(clipPreview('short')).toBe('short');
    expect(clipPreview(null)).toBe('');
  });
});

describe('isInbox / the clip inbox is not judged as a project', () => {
  it('recognises the inbox by name, whatever the casing', () => {
    expect(isInbox({ work_name: 'Inbox' })).toBe(true);
    expect(isInbox({ work_name: '  inbox ' })).toBe(true);
    expect(isInbox({ work_name: 'Inbox Zero' })).toBe(false);
    expect(isInbox({})).toBe(false);
    expect(isInbox(null)).toBe(false);
  });

  it('never shows the inbox as stale, however long it sits', () => {
    const ancient = new Date('2020-01-01').toISOString();
    const health = projectHealth({ work_name: 'Inbox', last_activity_at: ancient });
    expect(health.level).toBe('frozen');
    expect(health.reason).toMatch(/inbox/i);
  });

  it('still judges a normal project on the same data', () => {
    const ancient = new Date('2020-01-01').toISOString();
    expect(projectHealth({ work_name: 'Real', last_activity_at: ancient }).level).toBe('bad');
  });
});
