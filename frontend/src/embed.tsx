/**
 * Chat Widget Web Component entry point.
 *
 * Registers `<cuckoo-chat>` custom element using Shadow DOM for style isolation.
 * Reads configuration from data-* attributes or window.CuckooConfig.
 * Mounts the React ChatWidget inside the Shadow Root.
 *
 * Usage:
 *   <script src="https://cdn.cuckoo-echo.com/embed.js"
 *     data-api-key="ck_xxx"
 *     data-theme="light"
 *     data-position="bottom-right"
 *     data-lang="zh-CN">
 *   </script>
 *
 * Or via global config:
 *   <script>
 *     window.CuckooConfig = { apiKey: 'ck_xxx', theme: 'dark' };
 *   </script>
 *   <cuckoo-chat></cuckoo-chat>
 */

import { createRoot } from 'react-dom/client';
import ChatWidget from './pages/chat/ChatWidget';
import type { ChatWidgetProps } from './types';

// ─── Global config interface ──────────────────────────────────

type CuckooConfig = Partial<ChatWidgetProps>;

declare global {
  interface Window {
    CuckooConfig?: CuckooConfig;
  }
}

// ─── Shadow DOM styles ────────────────────────────────────────

function buildShadowStyles(
  theme: 'light' | 'dark',
  primaryColor?: string,
  bgColor?: string,
): string {
  const resolvedPrimary = primaryColor ?? (theme === 'dark' ? '#6366f1' : '#4f46e5');
  const resolvedBg = bgColor ?? (theme === 'dark' ? '#1e1e2e' : '#ffffff');
  const textColor = theme === 'dark' ? '#e2e8f0' : '#1e293b';

  return `
    :host {
      all: initial;
      display: block;
      contain: content;
    }

    .ce-root {
      font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
      color: ${textColor};
      --ce-primary-color: ${resolvedPrimary};
      --ce-bg-color: ${resolvedBg};
      box-sizing: border-box;
    }

    .ce-root *, .ce-root *::before, .ce-root *::after {
      box-sizing: inherit;
    }
  `;
}

// ─── Custom Element ───────────────────────────────────────────

class CuckooChatElement extends HTMLElement {
  private _root: ReturnType<typeof createRoot> | null = null;

  connectedCallback() {
    const shadow = this.attachShadow({ mode: 'open' });

    // Read props from data attributes, falling back to window.CuckooConfig
    const config: CuckooConfig = window.CuckooConfig ?? {};

    const apiKey = this.dataset.apiKey ?? config.apiKey ?? '';
    const theme = (this.dataset.theme ?? config.theme ?? 'light') as 'light' | 'dark';
    const position = (this.dataset.position ?? config.position ?? 'bottom-right') as
      | 'bottom-right'
      | 'bottom-left';
    const lang = (this.dataset.lang ?? config.lang ?? 'zh-CN') as 'zh-CN' | 'en';
    const primaryColor = config.primaryColor;
    const bgColor = config.bgColor;
    const logoUrl = config.logoUrl;

    // Inject theme CSS variables via inline stylesheet (no CSS leakage)
    const style = document.createElement('style');
    style.textContent = buildShadowStyles(theme, primaryColor, bgColor);
    shadow.appendChild(style);

    // Mount container
    const container = document.createElement('div');
    container.className = 'ce-root';
    container.setAttribute('data-theme', theme);
    shadow.appendChild(container);

    // Apply brand colors via style.setProperty on the container
    if (primaryColor) {
      container.style.setProperty('--ce-primary-color', primaryColor);
    }
    if (bgColor) {
      container.style.setProperty('--ce-bg-color', bgColor);
    }

    // Render React app inside Shadow Root
    this._root = createRoot(container);
    this._root.render(
      <ChatWidget
        apiKey={apiKey}
        theme={theme}
        position={position}
        lang={lang}
        primaryColor={primaryColor}
        bgColor={bgColor}
        logoUrl={logoUrl}
      />,
    );
  }

  disconnectedCallback() {
    // Cleanup React tree when element is removed from DOM
    this._root?.unmount();
    this._root = null;
  }
}

// ─── Register custom element ─────────────────────────────────

if (!customElements.get('cuckoo-chat')) {
  customElements.define('cuckoo-chat', CuckooChatElement);
}

// Auto-create element if loaded via <script> tag with data attributes
// (the script tag itself carries the config)
function autoMount() {
  // Only auto-mount if no <cuckoo-chat> element exists yet
  if (document.querySelector('cuckoo-chat')) return;

  // Find the script tag that loaded this file
  const scripts = document.querySelectorAll('script[data-api-key]');
  if (scripts.length === 0) return;

  const el = document.createElement('cuckoo-chat');
  const scriptEl = scripts[scripts.length - 1] as HTMLScriptElement;

  // Copy data attributes from script tag to custom element
  for (const attr of Array.from(scriptEl.attributes)) {
    if (attr.name.startsWith('data-')) {
      el.setAttribute(attr.name, attr.value);
    }
  }

  document.body.appendChild(el);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', autoMount);
} else {
  autoMount();
}
