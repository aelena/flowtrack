<script>
  import { chatWithProject } from '../api.js';

  export let projectId;

  let messages = [];
  let input = '';
  let loading = false;

  async function send() {
    if (!input.trim() || loading) return;
    const userMsg = input;
    input = '';
    messages = [...messages, { role: 'user', content: userMsg }];
    loading = true;

    try {
      const resp = await chatWithProject(projectId, userMsg);
      messages = [...messages, { role: 'assistant', content: resp.response }];
    } catch (e) {
      messages = [...messages, { role: 'assistant', content: `Error: ${e.message}` }];
    } finally {
      loading = false;
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }
</script>

<div class="chat-mode">
  <div class="messages">
    {#if messages.length === 0}
      <p class="empty">Start a conversation about this project...</p>
    {/if}
    {#each messages as msg}
      <div class="message {msg.role}">
        <div class="message-label">{msg.role === 'user' ? 'You' : 'Assistant'}</div>
        <div class="message-content">{msg.content}</div>
      </div>
    {/each}
    {#if loading}
      <div class="message assistant">
        <div class="message-label">Assistant</div>
        <div class="message-content typing">Thinking...</div>
      </div>
    {/if}
  </div>

  <div class="chat-input">
    <textarea
      bind:value={input}
      on:keydown={handleKeydown}
      placeholder="Ask about this project..."
      rows="2"
    ></textarea>
    <button class="primary" on:click={send} disabled={loading}>Send</button>
  </div>
</div>

<style>
  .chat-mode {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 400px;
  }

  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .empty {
    text-align: center;
    color: var(--text-muted);
    padding: 2rem;
  }

  .message {
    max-width: 80%;
    padding: 0.75rem;
    border-radius: var(--radius);
  }

  .message.user {
    align-self: flex-end;
    background: var(--accent);
    color: white;
  }

  .message.assistant {
    align-self: flex-start;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
  }

  .message-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    opacity: 0.7;
    margin-bottom: 0.25rem;
  }

  .message-content {
    font-size: 0.9rem;
    line-height: 1.5;
    white-space: pre-wrap;
  }

  .typing {
    opacity: 0.6;
    font-style: italic;
  }

  .chat-input {
    display: flex;
    gap: 0.5rem;
    padding: 0.75rem;
    border-top: 1px solid var(--border);
    background: var(--bg-secondary);
  }

  .chat-input textarea {
    flex: 1;
    resize: none;
  }

  .chat-input button {
    align-self: flex-end;
  }
</style>
