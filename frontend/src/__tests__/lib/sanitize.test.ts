import { sanitizeHtml } from '../../lib/sanitize';

describe('sanitizeHtml', () => {
  it('strips <script> tags', () => {
    const dirty = '<p>Hello</p><script>alert("xss")</script>';
    const result = sanitizeHtml(dirty);
    expect(result).not.toContain('<script');
    expect(result).not.toContain('alert');
    expect(result).toContain('<p>Hello</p>');
  });

  it('strips onclick attributes', () => {
    const dirty = '<div onclick="alert(1)">Click me</div>';
    const result = sanitizeHtml(dirty);
    expect(result).not.toContain('onclick');
    expect(result).toContain('Click me');
  });

  it('strips onerror attributes', () => {
    const dirty = '<img src="x" onerror="alert(1)">';
    const result = sanitizeHtml(dirty);
    expect(result).not.toContain('onerror');
  });

  it('strips javascript: protocol from links', () => {
    const dirty = '<a href="javascript:alert(1)">Click</a>';
    const result = sanitizeHtml(dirty);
    expect(result).not.toContain('javascript:');
  });

  it('preserves safe HTML tags (p, a, strong, code)', () => {
    const safe = '<p>Text with <a href="https://example.com">link</a> and <strong>bold</strong> and <code>code</code></p>';
    const result = sanitizeHtml(safe);
    expect(result).toContain('<p>');
    expect(result).toContain('<a');
    expect(result).toContain('<strong>');
    expect(result).toContain('<code>');
    expect(result).toContain('href="https://example.com"');
  });
});
