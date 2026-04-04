import DOMPurify from 'dompurify';

const ALLOWED_TAGS = [
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'p', 'br', 'hr',
  'ul', 'ol', 'li',
  'blockquote', 'pre', 'code',
  'a', 'strong', 'em', 'del', 'sub', 'sup',
  'table', 'thead', 'tbody', 'tr', 'th', 'td',
  'img',
  'span', 'div',
];

const ALLOWED_ATTR = [
  'href', 'src', 'alt', 'title', 'class',
  'width', 'height',
  'target', 'rel',
];

/**
 * Sanitize untrusted HTML using DOMPurify.
 * Strips <script>, on* event handlers, and javascript: protocol.
 */
export function sanitizeHtml(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed', 'form'],
    FORBID_ATTR: ['onerror', 'onclick', 'onload', 'onmouseover', 'onfocus', 'onblur'],
    ALLOW_DATA_ATTR: false,
  });
}
