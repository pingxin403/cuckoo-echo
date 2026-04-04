import type { WSClientOptions, WSMessage } from '@/types';

const HEARTBEAT_INTERVAL_MS = 30_000;

export class WSClient {
  private ws: WebSocket | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;
  private readonly maxReconnectDelay = 30_000;
  private intentionalClose = false;

  connect(options: WSClientOptions): void {
    this.intentionalClose = false;

    this.ws = new WebSocket(options.url);

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(String(event.data)) as WSMessage;
        options.onMessage(data);
      } catch {
        // Skip malformed JSON messages
      }
    };

    this.ws.onclose = () => {
      this.stopHeartbeat();
      options.onClose();
      if (!this.intentionalClose) {
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
