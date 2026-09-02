export function tsFilename(name, ext) {
  const slug = (name || 'project').replace(/\s+/g, '_');
  const d = new Date();
  const ts =
    d.getFullYear().toString() +
    String(d.getMonth() + 1).padStart(2, '0') +
    String(d.getDate()).padStart(2, '0') +
    '-' +
    String(d.getHours()).padStart(2, '0') +
    String(d.getMinutes()).padStart(2, '0') +
    String(d.getSeconds()).padStart(2, '0');
  return `${slug}-${ts}.${ext}`;
}

export function shortDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return (
    d.getFullYear() +
    '-' +
    String(d.getMonth() + 1).padStart(2, '0') +
    '-' +
    String(d.getDate()).padStart(2, '0')
  );
}

export function daysSince(iso, now = new Date()) {
  if (!iso) return null;
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return null;
  // Whole calendar days, not elapsed hours: something edited at 23:50 last night
  // reads as one day old, not as zero.
  const a = Date.UTC(then.getFullYear(), then.getMonth(), then.getDate());
  const b = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((b - a) / 86400000);
}

// --- Project health -------------------------------------------------------
//
// The thresholds. Kept here rather than inline so they can be read, argued with
// and changed in one place.
export const STALE_WARN_DAYS = 21;
export const STALE_BAD_DAYS = 60;
export const TARGET_WARN_DAYS = 14;

/**
 * A colour for a project, and the reason for it.
 *
 * The reason is not decoration. A traffic light nobody can interrogate gets
 * ignored within a week, so every colour comes back with the sentence that
 * produced it and the table puts it in a tooltip.
 *
 * Two things this deliberately does not use:
 *
 * Age since creation. It only ever goes one way, so a project would go red and
 * never be able to go green again, and a light that cannot improve is noise.
 *
 * Task completion. A project can be at 20 percent and perfectly healthy, and at
 * 95 percent and dead. The percentage answers a different question.
 *
 * Grey is the one that matters most here. Eight of these projects are on hold
 * because that was a decision, not an oversight, and painting a deliberate
 * freeze red is how the whole column stops being read.
 */
// The clip inbox is a holding pen, not a project: it has no target date, it is
// never "finished", and it is supposed to sit there collecting things. Judging
// it on staleness would light up the one row where staleness means nothing.
export const INBOX_NAME = 'Inbox';

export function isInbox(project) {
  return project?.work_name?.trim().toLowerCase() === INBOX_NAME.toLowerCase();
}

export function projectHealth(project, now = new Date()) {
  if (!project) return { level: 'unknown', reason: '' };

  if (isInbox(project)) return { level: 'frozen', reason: 'Clip inbox, not a project' };
  if (project.archived) return { level: 'frozen', reason: 'Archived' };
  if (project.status === 'on_hold') return { level: 'frozen', reason: 'On hold, by decision' };
  if (project.status === 'deprecated') return { level: 'frozen', reason: 'Dropped' };

  const idle = daysSince(project.last_activity_at, now);
  const complete = (project.task_completion ?? 0) >= 100;
  const untilTarget = project.desired_end_date ? -daysSince(project.desired_end_date, now) : null;

  // Past its date and not finished. The strongest signal available, and the
  // only one that is a fact rather than a heuristic.
  if (untilTarget !== null && untilTarget < 0 && !complete) {
    const late = Math.abs(untilTarget);
    return { level: 'bad', reason: `${late} day${late === 1 ? '' : 's'} past its target date` };
  }

  if (idle !== null && idle > STALE_BAD_DAYS) {
    return { level: 'bad', reason: `No activity in ${idle} days` };
  }

  if (untilTarget !== null && untilTarget >= 0 && untilTarget <= TARGET_WARN_DAYS && !complete) {
    return {
      level: 'warn',
      reason: `Target date in ${untilTarget} day${untilTarget === 1 ? '' : 's'}`,
    };
  }

  if (idle !== null && idle > STALE_WARN_DAYS) {
    return { level: 'warn', reason: `No activity in ${idle} days` };
  }

  if (idle === null) return { level: 'unknown', reason: 'No activity recorded' };

  return { level: 'good', reason: `Active, last touched ${idle} day${idle === 1 ? '' : 's'} ago` };
}

// Clips arrive from arbitrary web pages through the Chrome clipper, so
// source_url is attacker-controlled text, not a trusted link. Rendering it
// straight into an href would accept `javascript:` and `data:` payloads that
// run on click. Only the two schemes a page can legitimately be reached at
// come back; anything else is shown as inert text by the caller.
export function safeExternalUrl(url) {
  if (typeof url !== 'string' || !url.trim()) return null;
  try {
    const parsed = new URL(url, 'http://invalid.example');
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return null;
    if (parsed.hostname === 'invalid.example') return null; // was relative, so not a source
    return parsed.href;
  } catch {
    return null;
  }
}

// A clip is often a wall of text. The list shows the first lines and the full
// content stays one click away rather than pushing everything else off screen.
export function clipPreview(content, max = 240) {
  if (typeof content !== 'string') return '';
  const collapsed = content.replace(/\s+/g, ' ').trim();
  return collapsed.length > max ? collapsed.slice(0, max).trimEnd() + '…' : collapsed;
}
