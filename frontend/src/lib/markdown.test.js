import { describe, expect, it } from 'vitest';

import { renderMarkdown } from './markdown.js';

// These tests exist for one reason: renderMarkdown() feeds {@html} in two
// components, and its escaping is the only thing between the Chrome clipper —
// which stores snippets from arbitrary web pages — and stored XSS. If someone
// "simplifies" the escaping away, this file should be what stops them.
describe('renderMarkdown escaping', () => {
  it('neutralises a script tag', () => {
    const out = renderMarkdown('<script>alert(1)</script>');
    expect(out).not.toContain('<script>');
    expect(out).toContain('&lt;script&gt;');
  });

  it('neutralises an inline event handler', () => {
    const out = renderMarkdown('<img src=x onerror="alert(1)">');
    expect(out).not.toContain('<img');
    expect(out).toContain('&lt;img');
  });

  it('escapes quotes so an attribute cannot be broken out of', () => {
    const out = renderMarkdown(`a "double" and an 'single'`);
    expect(out).toContain('&quot;');
    expect(out).toContain('&#39;');
  });

  it('escapes ampersands before anything else, so entities cannot be smuggled', () => {
    expect(renderMarkdown('&lt;script&gt;')).toContain('&amp;lt;');
  });

  it('escapes html inside a fenced code block too', () => {
    const out = renderMarkdown('```\n<script>alert(1)</script>\n```');
    expect(out).not.toContain('<script>');
  });
});

describe('renderMarkdown rendering', () => {
  it('returns an empty string for empty input', () => {
    expect(renderMarkdown('')).toBe('');
    expect(renderMarkdown(null)).toBe('');
    expect(renderMarkdown(undefined)).toBe('');
  });

  it('renders headings, demoted so they do not clash with the page h1', () => {
    expect(renderMarkdown('# Title')).toContain('<h2>Title</h2>');
    expect(renderMarkdown('## Sub')).toContain('<h3>Sub</h3>');
    expect(renderMarkdown('### Deep')).toContain('<h4>Deep</h4>');
  });

  it('renders bold, italic and inline code', () => {
    expect(renderMarkdown('**bold**')).toContain('<strong>bold</strong>');
    expect(renderMarkdown('*italic*')).toContain('<em>italic</em>');
    expect(renderMarkdown('`code`')).toContain('<code>code</code>');
  });

  it('renders a fenced code block', () => {
    expect(renderMarkdown('```\nx = 1\n```')).toContain('<pre><code>');
  });

  it('renders list items', () => {
    expect(renderMarkdown('- one\n- two')).toContain('<li>one</li>');
  });

  it('turns single newlines into breaks', () => {
    expect(renderMarkdown('a\nb')).toContain('<br>');
  });
});
