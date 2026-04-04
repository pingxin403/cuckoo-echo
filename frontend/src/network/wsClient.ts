import type { WSClientOptions, WSMessage } from '@/types';

const HEARTBEAT_INTERVAL_MS = 30_000;

// ─── WS Close Code Handling ─────────────────────────────────────

const WS_NO_RECONNECT_CODES = new Set([1000, 4001]);

export class WSClient {
  private ws: WebSocket | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;
  private readonly maxReconnectDelay = 30_000;
  private intentionalClose = false;

  connect(options: WSClientOptions): void {
    this.intentionalClose = false;

    // Build URL with queryParams
    let wsUrl = options.url;
    if (options.queryParams && Object.keys(options.queryParams).length > 0) {
      const url = new URL(options.url);
      for (const [key, value] of Object.entries(options.queryParams)) {
        url.searchParams.set(key, value);
      }
      wsUrl = url.toString();
    }

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
      this.startHeartbeat();
      options.onOpen?.();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(String(event.data)) as WSMessage;
        options.onMessage(data);
      } catch {
        // Skip malformed JSON messages
      }
    };

    this.ws.onclose = (event: CloseEvent) => {
      this.stopHeartbeat();
      options.onClose();
      // Don't reconnect for intentional close or specific close codes
      if (!this.intentionalClose && !WS_NO_RECONNECT_CODES.has(event.code)) {
        this.scheduleReconnect(options);
      }
    };

    this.ws.onerror = (error: Event) => {
      options.onError(error);
    };
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.stopHeartbeat();
    this.clearReconnect();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data: object): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  // ── internal ──────────────────────────────────────────────────

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: 'ping' });
    }, HEARTBEAT_INTERVAL_MS);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer !== null) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private clearReconnect(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private scheduleReconnect(options: WSClientOptions): void {
    this.clearReconnect();
    const delay = this.reconnectDelay;
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect(options);
    }, delay);
  }
}
