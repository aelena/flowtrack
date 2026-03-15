<script>
  export let content = '';
  export let onSave = () => {};

  let previewHtml = '';

  function renderMarkdown(text) {
    return text
      .replace(/^### (.+)$/gm, '<h4>$1</h4>')
      .replace(/^## (.+)$/gm, '<h3>$1</h3>')
      .replace(/^# (.+)$/gm, '<h2>$1</h2>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`{3}([\s\S]*?)`{3}/g, '<pre><code>$1</code></pre>')
      .replace(/`(.+?)`/g, '<code>$1</code>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');
  }

  $: previewHtml = renderMarkdown(content);
</script>

<div class="write-mode">
  <div class="editor-pane">
    <div class="pane-header">Markdown</div>
    <textarea
      class="markdown-editor"
      bind:value={content}
      on:input={() => onSave(content)}
      placeholder="Write markdown here..."
    ></textarea>
  </div>

  <div class="divider"></div>

  <div class="preview-pane">
    <div class="pane-header">Preview</div>
    <div class="preview-content">
      {@html previewHtml}
    </div>
  </div>
</div>

<style>
  .write-mode {
    display: flex;
    height: 100%;
    min-height: 400px;
    gap: 0;
  }

  .editor-pane, .preview-pane {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .pane-header {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--border);
    font-weight: 600;
  }

  .markdown-editor {
    flex: 1;
    border: none;
    border-radius: 0;
    resize: none;
    font-family: var(--font-mono);
    font-size: 0.9rem;
    padding: 0.75rem;
    line-height: 1.6;
    background: var(--bg);
  }

  .markdown-editor:focus {
    outline: none;
  }

  .divider {
    width: 1px;
    background: var(--border);
  }

  .preview-content {
    flex: 1;
    padding: 0.75rem;
    overflow-y: auto;
    font-size: 0.9rem;
    line-height: 1.6;
  }

  .preview-content :global(h2) { font-size: 1.4rem; margin: 0.5rem 0; }
  .preview-content :global(h3) { font-size: 1.2rem; margin: 0.5rem 0; }
  .preview-content :global(h4) { font-size: 1.05rem; margin: 0.5rem 0; }
  .preview-content :global(code) {
    background: var(--bg-tertiary);
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
    font-family: var(--font-mono);
    font-size: 0.85rem;
  }
  .preview-content :global(pre) {
    background: var(--bg-secondary);
    padding: 0.75rem;
    border-radius: var(--radius);
    overflow-x: auto;
  }
  .preview-content :global(pre code) {
    background: none;
    padding: 0;
  }
  .preview-content :global(ul) {
    padding-left: 1.5rem;
    margin: 0.5rem 0;
  }
  .preview-content :global(strong) { font-weight: 600; }
</style>
