<script>
  import { projects, language } from '$lib/stores.js';
  import { t } from '$lib/i18n.js';

  let lang = 'en';
  language.subscribe(v => lang = v);
</script>

<div class="home">
  <div class="welcome">
    <h1>FlowTrack</h1>
    <p>Select a project from the sidebar to get started, or create a new one.</p>
  </div>

  {#if $projects.length > 0}
    <div class="recent">
      <h2>Recent {t('projects', lang)}</h2>
      <div class="project-grid">
        {#each $projects.slice(0, 6) as project}
          <a href="/projects/{project.id}" class="project-card">
            <h3>{project.work_name}</h3>
            <div class="card-meta">
              {#if project.star_rating}
                <span class="stars">{'★'.repeat(project.star_rating)}{'☆'.repeat(5 - project.star_rating)}</span>
              {/if}
              <div class="progress-bar" style="margin-top: 0.5rem;">
                <div class="fill" style="width: {project.task_completion}%"></div>
              </div>
              <span class="completion-text">{project.task_completion}% complete</span>
            </div>
          </a>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .home {
    flex: 1;
    padding: 2rem;
    max-width: 800px;
    margin: 0 auto;
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

  .recent {
    margin-top: 2rem;
  }

  .recent h2 {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 1rem;
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
    transition: box-shadow var(--transition), border-color var(--transition);
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
</style>
