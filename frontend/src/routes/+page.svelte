<script>
  import { onMount } from 'svelte';
  import { homeView, language } from '$lib/stores.js';
  import { listProjects, getThroughput } from '$lib/api.js';
  import { t } from '$lib/i18n.js';
  import { daysSince, projectHealth, shortDate } from '$lib/utils.js';

  let lang = 'en';
  language.subscribe((v) => (lang = v));

  // Deliberately not the `projects` store. That one belongs to the sidebar and
  // carries whatever search, area and tag filters are set there, so reading it
  // here meant the home page changed when you typed in the sidebar. This page
  // asks for its own list, ordered by real activity.
  let rows = [];
  let loading = true;
  let loadError = '';

  // Throughput is a nice-to-have on this page. It loads separately and its
  // failure is silent, because a metrics endpoint being down is no reason to
  // withhold the project list.
  let flow = null;

  onMount(async () => {
    getThroughput(12)
      .then((data) => (flow = data))
      .catch(() => (flow = null));

    try {
      rows = await listProjects({ sort_by: 'last_activity_at', sort_order: 'desc' });
    } catch (e) {
      loadError = e.message || 'Could not load projects';
    } finally {
      loading = false;
    }
  });

  const ARROW = { up: '↑', down: '↓', flat: '→' };

  /** Points for a sparkline, scaled to the tallest week rather than to zero. */
  function sparkPoints(weeks, width = 132, height = 26) {
    if (!weeks || weeks.length < 2) return '';
    const peak = Math.max(...weeks.map((w) => w.completed), 1);
    const step = width / (weeks.length - 1);
    return weeks
      .map(
        (w, i) => `${(i * step).toFixed(1)},${(height - (w.completed / peak) * height).toFixed(1)}`
      )
      .join(' ');
  }

  const name = (p) => p.final_name || p.work_name || '';

  // --- table state ---------------------------------------------------------
  let query = '';
  let sortKey = 'last_activity_at';
  let sortAsc = false;
  let page = 0;
  const PER_PAGE = 15;

  const COLUMNS = [
    // Unlabelled and unsortable: it is a dot, and sorting by colour would sort
    // by a category the reader cannot see the order of.
    { key: null, label: 'colHealth', align: 'left' },
    { key: 'name', label: 'colProject', align: 'left' },
    { key: 'status', label: 'colStatus', align: 'left' },
    { key: 'star_rating', label: 'colStars', align: 'left' },
    { key: 'task_completion', label: 'colCompletion', align: 'right' },
    { key: 'desired_end_date', label: 'colTarget', align: 'right' },
    { key: 'last_activity_at', label: 'colActivity', align: 'right' },
  ];

  // "Search by any field" taken literally: every value a row displays plus the
  // ones it does not, flattened once per row so typing stays cheap.
  function haystack(p) {
    return [
      name(p),
      p.work_name,
      p.final_name,
      p.status,
      (p.tags || []).join(' '),
      p.star_rating,
      p.task_completion,
      p.subjective_completion,
      shortDate(p.desired_end_date),
      shortDate(p.created_at),
      shortDate(p.updated_at),
      shortDate(p.last_activity_at),
    ]
      .filter((v) => v !== null && v !== undefined && v !== '')
      .join(' ')
      .toLowerCase();
  }

  function value(p, key) {
    if (key === 'name') return name(p).toLowerCase();
    if (key === 'last_activity_at' || key === 'desired_end_date') {
      const raw = p[key];
      // Rows with no target date sort last in either direction rather than
      // pretending to be the epoch.
      return raw ? new Date(raw).getTime() : null;
    }
    const v = p[key];
    return v === null || v === undefined ? null : v;
  }

  function compare(a, b) {
    const va = value(a, sortKey);
    const vb = value(b, sortKey);
    if (va === null && vb === null) return 0;
    if (va === null) return 1;
    if (vb === null) return -1;
    if (va < vb) return sortAsc ? -1 : 1;
    if (va > vb) return sortAsc ? 1 : -1;
    return name(a).localeCompare(name(b));
  }

  function sortBy(key) {
    if (sortKey === key) {
      sortAsc = !sortAsc;
    } else {
      sortKey = key;
      // Names read best A to Z; everything else is more useful biggest first.
      sortAsc = key === 'name';
    }
    page = 0;
  }

  $: filtered = query.trim()
    ? rows.filter((p) => haystack(p).includes(query.trim().toLowerCase()))
    : rows;
  $: sorted = [...filtered].sort(compare);
  $: pageCount = Math.max(1, Math.ceil(sorted.length / PER_PAGE));
  // Filtering can strand the reader on a page that no longer exists.
  $: if (page > pageCount - 1) page = pageCount - 1;
  $: pageRows = sorted.slice(page * PER_PAGE, page * PER_PAGE + PER_PAGE);
  $: recent = rows.slice(0, 6);

  function activityLabel(iso) {
    const d = daysSince(iso);
    if (d === null) return '';
    if (d === 0) return t('today', lang);
    return d + t('daysAgo', lang);
  }
</script>

<div class="home">
  <div class="welcome">
    <h1>FlowTrack</h1>
    <p>Select a project from the sidebar to get started, or create a new one.</p>
  </div>

  {#if flow}
    <div class="flow">
      <div class="card">
        <span class="card-label">{t('thisWeek', lang)}</span>
        <span class="card-number">{flow.last_7_days}</span>
        <span class="card-delta card-delta--{flow.trend}">
          {ARROW[flow.trend]}
          {flow.change > 0 ? '+' : ''}{flow.change}
          <span class="card-vs">vs {flow.previous_7_days} {t('lastWeek', lang)}</span>
        </span>
      </div>

      <div class="card card--wide">
        <span class="card-label">{t('twelveWeeks', lang)}</span>
        <svg class="spark" viewBox="0 0 132 26" preserveAspectRatio="none" aria-hidden="true">
          <polyline points={sparkPoints(flow.weeks)} fill="none" stroke="currentColor" />
        </svg>
        <span class="card-range">
          {flow.weeks[0]?.week_start} &rarr; {flow.weeks[flow.weeks.length - 1]?.week_start}
        </span>
      </div>
    </div>

    {#if flow.estimated_counted > 0}
      <!-- Said out loud rather than buried. Most of this history predates the
           column that records a completion date, so it was filled in from when
           the row last changed. Close for most, late for anything edited after
           it was closed. -->
      <p class="flow-note">
        {flow.estimated_counted} / {flow.total_counted}
        {t('estimatedNote', lang)}
      </p>
    {/if}
  {/if}

  <div class="view-switch" role="tablist">
    <button
      role="tab"
      aria-selected={$homeView === 'recent'}
      class:active={$homeView === 'recent'}
      on:click={() => homeView.set('recent')}
    >
      {t('recentProjects', lang)}
    </button>
    <button
      role="tab"
      aria-selected={$homeView === 'all'}
      class:active={$homeView === 'all'}
      on:click={() => homeView.set('all')}
    >
      {t('allProjects', lang)}
      {#if rows.length}<span class="count">{rows.length}</span>{/if}
    </button>
  </div>

  {#if loading}
    <p class="muted">Loading...</p>
  {:else if loadError}
    <p class="error">{loadError}</p>
  {:else if rows.length === 0}
    <p class="muted">{t('noProjects', lang)}</p>
  {:else if $homeView === 'recent'}
    <div class="project-grid">
      {#each recent as project (project.id)}
        <a href="/projects/{project.id}" class="project-card">
          <h3>{name(project)}</h3>
          <div class="card-meta">
            {#if project.star_rating}
              <span class="stars"
                >{'★'.repeat(project.star_rating)}{'☆'.repeat(5 - project.star_rating)}</span
              >
            {/if}
            <div class="progress-bar" style="margin-top: 0.5rem;">
              <div class="fill" style="width: {project.task_completion}%"></div>
            </div>
            <span class="completion-text">
              {project.task_completion}% complete
              <span class="dot">·</span>
              {activityLabel(project.last_activity_at)}
            </span>
          </div>
        </a>
      {/each}
    </div>
  {:else}
    <div class="table-tools">
      <input
        type="search"
        bind:value={query}
        placeholder={t('filterAny', lang)}
        aria-label={t('filterAny', lang)}
      />
      <span class="muted small">
        {t('showing', lang)}
        {sorted.length === 0 ? 0 : page * PER_PAGE + 1}–{Math.min(
          (page + 1) * PER_PAGE,
          sorted.length
        )}
        / {sorted.length}
      </span>
    </div>

    {#if sorted.length === 0}
      <p class="muted">{t('noMatches', lang)}</p>
    {:else}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              {#each COLUMNS as col}
                <th class:num={col.align === 'right'}>
                  {#if col.key}
                    <button on:click={() => sortBy(col.key)} class:sorted={sortKey === col.key}>
                      {t(col.label, lang)}
                      <span class="arrow">{sortKey === col.key ? (sortAsc ? '↑' : '↓') : ''}</span>
                    </button>
                  {/if}
                </th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each pageRows as p (p.id)}
              {@const health = projectHealth(p)}
              <tr>
                <td class="health-cell">
                  <span
                    class="dot dot--{health.level}"
                    title={health.reason}
                    aria-label={health.reason}
                    role="img"
                  ></span>
                </td>
                <td><a href="/projects/{p.id}">{name(p)}</a></td>
                <td><span class="status status--{p.status}">{p.status}</span></td>
                <td class="stars">
                  {p.star_rating ? '★'.repeat(p.star_rating) : ''}
                </td>
                <td class="num">
                  <div class="cell-bar" title="{p.task_completion}%">
                    <div class="fill" style="width: {p.task_completion}%"></div>
                  </div>
                  <span class="pct">{p.task_completion}%</span>
                </td>
                <td class="num">{shortDate(p.desired_end_date) || '—'}</td>
                <td class="num" title={p.last_activity_at || ''}>
                  {shortDate(p.last_activity_at)}
                  <span class="ago">{activityLabel(p.last_activity_at)}</span>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      {#if pageCount > 1}
        <div class="pager">
          <button on:click={() => (page = Math.max(0, page - 1))} disabled={page === 0}>←</button>
          <span class="muted small">{page + 1} / {pageCount}</span>
          <button
            on:click={() => (page = Math.min(pageCount - 1, page + 1))}
            disabled={page >= pageCount - 1}>→</button
          >
        </div>
      {/if}
    {/if}
  {/if}
</div>

<style>
  .home {
    flex: 1;
    padding: 2rem;
    max-width: 1100px;
    margin: 0 auto;
    width: 100%;
  }

  .welcome {
    text-align: center;
    padding: 3rem 0 2rem;
  }

  .welcome h1 {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }

  .welcome p {
    color: var(--text-secondary);
    font-size: 1rem;
  }

  .view-switch {
    display: flex;
    gap: 0.25rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.25rem;
  }

  .view-switch button {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 0.5rem 0.75rem;
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-secondary);
    cursor: pointer;
    margin-bottom: -1px;
  }

  .view-switch button.active {
    color: var(--text);
    border-bottom-color: var(--accent);
  }

  .count {
    font-weight: 400;
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .muted {
    color: var(--text-muted);
  }

  .small {
    font-size: 0.75rem;
  }

  .error {
    color: #c0392b;
  }

  .project-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 1rem;
  }

  .project-card {
    display: block;
    padding: 1rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    text-decoration: none;
    color: var(--text);
    transition:
      box-shadow var(--transition),
      border-color var(--transition);
  }

  .project-card:hover {
    border-color: var(--accent);
    box-shadow: 0 2px 12px var(--shadow);
    text-decoration: none;
  }

  .project-card h3 {
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
  }

  .stars {
    color: #f5a623;
    font-size: 0.8rem;
  }

  .completion-text {
    font-size: 0.7rem;
    color: var(--text-muted);
    margin-top: 0.25rem;
    display: block;
  }

  .dot {
    opacity: 0.5;
  }

  .table-tools {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.75rem;
  }

  .table-tools input {
    flex: 1;
    max-width: 22rem;
    padding: 0.4rem 0.6rem;
    font-size: 0.85rem;
    background: var(--bg-secondary);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }

  /* The table has to be able to scroll on its own, or a long project name
     pushes the whole page sideways on a narrow window. */
  .table-wrap {
    overflow-x: auto;
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }

  th,
  td {
    padding: 0.45rem 0.7rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }

  tbody tr:last-child td {
    border-bottom: none;
  }

  th {
    background: var(--bg-secondary);
    position: sticky;
    top: 0;
  }

  th.num,
  td.num {
    text-align: right;
  }

  th button {
    background: none;
    border: none;
    padding: 0;
    font: inherit;
    font-weight: 600;
    color: var(--text-secondary);
    cursor: pointer;
  }

  th button.sorted {
    color: var(--text);
  }

  .arrow {
    font-size: 0.7rem;
  }

  tbody tr:hover {
    background: var(--bg-secondary);
  }

  td a {
    color: var(--text);
    text-decoration: none;
    font-weight: 500;
  }

  td a:hover {
    color: var(--accent);
  }

  .status {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-muted);
  }

  .cell-bar {
    display: inline-block;
    vertical-align: middle;
    width: 60px;
    height: 4px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
    margin-right: 0.4rem;
  }

  .cell-bar .fill {
    height: 100%;
    background: var(--accent);
  }

  .pct {
    font-variant-numeric: tabular-nums;
  }

  .ago {
    color: var(--text-muted);
    font-size: 0.7rem;
    margin-left: 0.35rem;
  }

  .pager {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    margin-top: 0.85rem;
  }

  .pager button {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    padding: 0.2rem 0.6rem;
    cursor: pointer;
  }

  .pager button:disabled {
    opacity: 0.4;
    cursor: default;
  }

  /* --- throughput ------------------------------------------------------- */

  .flow {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin: 0 0 0.5rem 0;
  }

  .card {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    padding: 0.6rem 0.85rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-secondary);
    min-width: 9rem;
  }

  .card--wide {
    flex: 1;
    min-width: 14rem;
    color: var(--text-secondary);
  }

  .card-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-secondary);
  }

  .card-number {
    font-size: 1.6rem;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
    color: var(--text);
  }

  .card-delta {
    font-size: 0.75rem;
    font-variant-numeric: tabular-nums;
  }

  .card-delta--up {
    color: #2e7d32;
  }

  .card-delta--down {
    color: #c0392b;
  }

  .card-delta--flat {
    color: var(--text-secondary);
  }

  .card-vs {
    color: var(--text-secondary);
  }

  .spark {
    width: 100%;
    height: 26px;
    margin: 0.25rem 0;
    stroke-width: 1.4;
    vector-effect: non-scaling-stroke;
  }

  .card-range {
    font-size: 0.68rem;
    font-variant-numeric: tabular-nums;
  }

  .flow-note {
    margin: 0 0 0.75rem 0;
    font-size: 0.72rem;
    color: var(--text-secondary);
  }

  /* --- health dot ------------------------------------------------------- */

  .health-cell {
    width: 1.2rem;
    padding-right: 0;
  }

  .dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    /* A ring rather than a bare fill, so the grey one still reads as a
       deliberate state and not as a missing value. */
    box-shadow: 0 0 0 1px var(--bg-secondary);
  }

  .dot--good {
    background: #2e7d32;
  }

  .dot--warn {
    background: #e08a00;
  }

  .dot--bad {
    background: #c0392b;
  }

  .dot--frozen {
    background: #9aa0a6;
  }

  .dot--unknown {
    background: transparent;
    box-shadow: inset 0 0 0 1px var(--border);
  }
</style>
