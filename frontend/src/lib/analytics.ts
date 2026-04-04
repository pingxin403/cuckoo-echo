let consentGranted = false;

/**
 * Set user privacy consent status.
 * Analytics events are only reported when consent is granted.
 */
export function setConsent(granted: boolean): void {
  consentGranted = granted;
}

export const analytics = {
  /**
   * Track an analytics event.
   * No-op in non-production environments or when consent is not granted.
   */
  track(event: string, params?: Record<string, unknown>): void {
    if (!import.meta.env.PROD) return;
    if (!consentGranted) return;

    // Unified analytics interface — plug in PostHog, Mixpanel, or custom backend here
    console.info('[analytics]', event, params);
  },
};
