<script>
  import { language } from '../stores.js';
  import {
    generatePRD,
    generateBRD,
    generateMRD,
    generateSocial,
    suggestNextSteps,
    exportProject,
    getPending,
  } from '../api.js';
  import { t } from '../i18n.js';
  import { tsFilename } from '../utils.js';

  export let projectId;
  export let localDir = '';
  export let projectName = '';

  let output = null;
  let outputTitle = '';
  let showOutput = false;
  let canDownload = false;
  let downloadFilename = '';

  function downloadJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function run(action) {
    try {
      let result;
      canDownload = false;
      switch (action) {
        case 'prd':
          result = await generatePRD(projectId);
          outputTitle = 'PRD';
          canDownload = true;
          downloadFilename = tsFilename(projectName + '-PRD', 'json');
          break;
        case 'brd':
          result = await generateBRD(projectId);
          outputTitle = 'BRD';
          canDownload = true;
          downloadFilename = tsFilename(projectName + '-BRD', 'json');
          break;
        case 'mrd':
          result = await generateMRD(projectId);
          outputTitle = 'MRD';
          canDownload = true;
          downloadFilename = tsFilename(projectName + '-MRD', 'json');
          break;
        case 'social':
          result = await generateSocial(projectId);
          outputTitle = 'Social Content';
          break;
        case 'suggest':
          result = await suggestNextSteps(projectId);
          outputTitle = 'Suggestions';
          break;
        case 'pending':
          result = await getPending(projectId);
          outputTitle = 'Pending Items';
          break;
        case 'export': {
          const blob = await exportProject(projectId);
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = tsFilename(projectName, 'zip');
          a.click();
          URL.revokeObjectURL(url);
          return;
        }
        case 'cli':
          result = { command: `cd "${localDir}" && claude` };
          outputTitle = 'Claude CLI';
          break;
      }
      output = result;
      showOutput = true;
    } catch (e) {
      output = { error: e.message };
      outputTitle = 'Error';
      canDownload = false;
      showOutput = true;
    }
  }
</script>

<div class="command-bar">
  <h3>{t('commands', $language)}</h3>
  <div class="command-groups">
    <div class="command-group">
      <span class="group-label">Documents</span>
      <div class="command-row">
        <button on:click={() => run('prd')}>
          <svg viewBox="0 0 16 16" class="cmd-icon"
            ><path
              d="M4 1h6l4 4v10H4V1z"
              stroke="currentColor"
              fill="none"
              stroke-width="1.2"
            /><path d="M10 1v4h4" stroke="currentColor" fill="none" stroke-width="1.2" /></svg
          >
          PRD
        </button>
        <button on:click={() => run('brd')}>
          <svg viewBox="0 0 16 16" class="cmd-icon"
            ><path
              d="M4 1h6l4 4v10H4V1z"
              stroke="currentColor"
              fill="none"
              stroke-width="1.2"
            /><path d="M10 1v4h4" stroke="currentColor" fill="none" stroke-width="1.2" /></svg
          >
          BRD
        </button>
        <button on:click={() => run('mrd')}>
          <svg viewBox="0 0 16 16" class="cmd-icon"
            ><path
              d="M4 1h6l4 4v10H4V1z"
              stroke="currentColor"
              fill="none"
              stroke-width="1.2"
            /><path d="M10 1v4h4" stroke="currentColor" fill="none" stroke-width="1.2" /></svg
          >
          MRD
        </button>
        <button on:click={() => run('social')}>
          <svg viewBox="0 0 16 16" class="cmd-icon"
            ><circle
              cx="8"
              cy="8"
              r="6"
              stroke="currentColor"
              fill="none"
              stroke-width="1.2"
            /><path d="M5 6h6M5 8h4M5 10h5" stroke="currentColor" stroke-width="0.8" /></svg
          >
          Social
        </button>
      </div>
    </div>
    <div class="command-group">
      <span class="group-label">Actions</span>
      <div class="command-row">
        <button on:click={() => run('suggest')}>
          <svg viewBox="0 0 16 16" class="cmd-icon"
            ><circle
              cx="8"
              cy="6"
              r="4"
              stroke="currentColor"
              fill="none"
              stroke-width="1.2"
            /><path d="M6 10v3h4v-3" stroke="currentColor" fill="none" stroke-width="1.2" /></svg
          >
          Suggest
        </button>
        <button on:click={() => run('pending')}>
          <svg viewBox="0 0 16 16" class="cmd-icon"
            ><rect
              x="3"
              y="2"
              width="10"
              height="12"
              rx="1"
              stroke="currentColor"
              fill="none"
              stroke-width="1.2"
            /><path d="M6 5h4M6 8h4M6 11h2" stroke="currentColor" stroke-width="0.8" /></svg
          >
          Pending
        </button>
        <button on:click={() => run('export')}>
          <svg viewBox="0 0 16 16" class="cmd-icon"
            ><path
              d="M8 2v7M5 6l3 3 3-3M3 11v2h10v-2"
              stroke="currentColor"
              stroke-width="1.3"
              fill="none"
              stroke-linecap="round"
              stroke-linejoin="round"
            /></svg
          >
          ZIP
        </button>
        <button on:click={() => run('cli')}>
          <svg viewBox="0 0 16 16" class="cmd-icon"
            ><rect
              x="2"
              y="3"
              width="12"
              height="10"
              rx="1"
              stroke="currentColor"
              fill="none"
              stroke-width="1.2"
            /><path
              d="M5 7l2 2-2 2"
              stroke="currentColor"
              stroke-width="1.2"
              fill="none"
              stroke-linecap="round"
              stroke-linejoin="round"
            /><path
              d="M9 11h3"
              stroke="currentColor"
              stroke-width="1.2"
              stroke-linecap="round"
            /></svg
          >
          CLI
        </button>
      </div>
    </div>
  </div>
</div>

{#if showOutput}
  <div class="modal-overlay" role="presentation" on:click|self={() => (showOutput = false)}>
    <div class="modal" style="max-width: 600px;">
      <div class="modal-header">
        <h3>{outputTitle}</h3>
        <div class="modal-header-actions">
          {#if canDownload}
            <button class="primary" on:click={() => downloadJSON(output, downloadFilename)}>
              <svg viewBox="0 0 16 16" class="btn-icon"
                ><path
                  d="M8 2v7M5 6l3 3 3-3M3 11v2h10v-2"
                  stroke="currentColor"
                  stroke-width="1.5"
                  fill="none"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                /></svg
              >
              Download {downloadFilename}
            </button>
          {/if}
        </div>
      </div>
      <pre class="output">{JSON.stringify(output, null, 2)}</pre>
      <div class="modal-actions">
        <button
          on:click={() => {
            navigator.clipboard.writeText(JSON.stringify(output, null, 2));
          }}>Copy</button
        >
        <button on:click={() => (showOutput = false)}>Close</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .command-bar {
    margin: 1rem 0;
    padding: 0.75rem;
    background: var(--bg-secondary);
    border-radius: var(--radius);
  }
  .command-bar h3 {
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
  }

  .command-groups {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  .command-group {
  }
  .group-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    font-weight: 600;
  }
  .command-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-top: 0.3rem;
  }
  .command-row button {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.75rem;
    padding: 0.3rem 0.6rem;
  }
  .cmd-icon {
    width: 13px;
    height: 13px;
    flex-shrink: 0;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }
  .modal-header h3 {
    margin: 0;
  }
  .modal-header-actions {
    display: flex;
    gap: 0.5rem;
  }
  .btn-icon {
    width: 14px;
    height: 14px;
  }

  .output {
    background: var(--bg-secondary);
    padding: 0.75rem;
    border-radius: var(--radius);
    font-family: var(--font-mono);
    font-size: 0.8rem;
    max-height: 400px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
    margin: 0.75rem 0;
  }
  .modal-actions {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }
</style>
