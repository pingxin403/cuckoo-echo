import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock react-dom/client to avoid React rendering issues in jsdom
const mockRender = vi.fn();
const mockUnmount = vi.fn();
vi.mock('react-dom/client', () => ({
  createRoot: vi.fn(() => ({
    render: mockRender,
    unmount: mockUnmount,
  })),
}));

// Mock ChatWidget to avoid pulling in the full component tree
vi.mock('@/pages/chat/ChatWidget', () => ({
  default: () => null,
}));

describe('embed.tsx — <cuckoo-chat> Web Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete window.CuckooConfig;
  });

  afterEach(() => {
    // Clean up any cuckoo-chat elements from the DOM
    document.querySelectorAll('cuckoo-chat').forEach((el) => el.remove());
  });

  it('registers <cuckoo-chat> custom element after import', async () => {
    // Import triggers the customElements.define call
    await import('@/embed');
    expect(customElements.get('cuckoo-chat')).toBeDefined();
  });

  it('reads data-* attributes correctly', async () => {
    await import('@/embed');

    const el = document.createElement('cuckoo-chat');
    el.setAttribute('data-api-key', 'ck_test_123');
    el.setAttribute('data-theme', 'dark');
    el.setAttribute('data-position', 'bottom-left');
    el.setAttribute('data-lang', 'en');

    expect(el.dataset.apiKey).toBe('ck_test_123');
    expect(el.dataset.theme).toBe('dark');
    expect(el.dataset.position).toBe('bottom-left');
    expect(el.dataset.lang).toBe('en');
  });

  it('creates Shadow DOM with style and .ce-root container on connectedCallback', async () => {
    await import('@/embed');

    const el = document.createElement('cuckoo-chat');
    el.setAttribute('data-api-key', 'ck_abc');
    el.setAttribute('data-theme', 'light');

    // jsdom may not auto-fire connectedCallback, so we append and call manually if needed
    document.body.appendChild(el);

    // If connectedCallback didn't fire automatically, invoke it manually
    if (!el.shadowRoot) {
      (el as unknown as { connectedCallback: () => void }).connectedCallback();
    }

    // Shadow root should exist
    expect(el.shadowRoot).not.toBeNull();

    // Should contain a <style> element
    const styleEl = el.shadowRoot!.querySelector('style');
    expect(styleEl).not.toBeNull();
    expect(styleEl!.textContent).toContain(':host');
    expect(styleEl!.textContent).toContain('.ce-root');

    // Should contain a .ce-root container div
    const rootDiv = el.shadowRoot!.querySelector('.ce-root');
    expect(rootDiv).not.toBeNull();
    expect(rootDiv!.getAttribute('data-theme')).toBe('light');

    // createRoot should have been called to mount React
    const { createRoot } = await import('react-dom/client');
    expect(createRoot).toHaveBeenCalled();
    expect(mockRender).toHaveBeenCalled();

    // Cleanup
    el.remove();
  });
});
