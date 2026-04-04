import type { SSEClientOptions } from '@/types';

const STREAM_TIMEOUT_MS = 60_000;

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export class SSEClient {
  private controller: AbortController | null = null;
  private reconnectDelay = 1000;
  private readonly maxReconnectDelay = 30_000;
  private timeoutTimer: ReturnType<typeof setTimeout> | null = null;

  async connect(options: SSEClientOptions): Promise<void> {
    this.controller = new AbortController();

    let response: Response;
    try {
      response = await fetch(options.url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${options.apiKey}`,
        },
        body: JSON.stringify(options.body),
        signal: this.controller.signal,
      });
    } catch (err: unknown) {
      if ((err as DOMException)?.name === 'AbortError') return;
      options.onError({ code: 'NETWORK_ERROR', message: String(err) });
      return;
    }

    if (!response.ok) {
      options.onError({
        code: 'HTTP_ERROR',
        message: `HTTP ${String(response.status)}`,
      });
      return;
    }

    // Successful connection → reset backoff
    this.reconnectDelay = 1000;

    const body = response.body;
    if (!body) {
      options.onError({ code: 'NO_BODY', message: 'Response body is null' });
      return;
    }

    const reader = body.getReader();
    const decoder = new TextDecoder();
    await this.parseStream(reader, decoder, options);
  }

  disconnect(): void {
    this.clearTimeout();
    this.controller?.abort();
    this.controller = null;
  }

  async reconnect(options: SSEClientOptions): Promise<void> {
    await sleep(this.reconnectDelay);
    this.reconnectDelay = Math.min(
      this.reconnectDelay * 2,
      this.maxReconnectDelay,
    );
    await this.connect(options);
  }

  // ── internal ──────────────────────────────────────────────────

  private resetTimeout(options: SSEClientOptions): void {
    this.clearTimeout();
    this.timeoutTimer = setTimeout(() => {
      this.disconnect();
      options.onError({
        code: 'STREAM_TIMEOUT',
        message: `No data received for ${String(STREAM_TIMEOUT_MS / 1000)}s`,
      });
    }, STREAM_TIMEOUT_MS);
  }

  private clearTimeout(): void {
    if (this.timeoutTimer !== null) {
      clearTimeout(this.timeoutTimer);
      this.timeoutTimer = null;
    }
  }

  private async parseStream(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    decoder: TextDecoder,
    options: SSEClientOptions,
  ): Promise<void> {
    let buffer = '';
    let lastMessageId = '';

    // Start the 60s inactivity timer
    this.resetTimeout(options);

    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete lines
        const lines = buffer.split('\n');
        // Keep the last (possibly incomplete) chunk
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed === '') continue;

          if (!trimmed.startsWith('data:')) continue;

          const payload = trimmed.slice(5).trim();

          if (payload === '[DONE]') {
            this.clearTimeout();
            options.onDone(lastMessageId);
            return;
          }

          // Parse the JSON chunk
          try {
            const parsed: {
              id?: string;
              choices?: { delta?: { content?: string }; index?: number }[];
            } = JSON.parse(payload) as {
              id?: string;
              choices?: { delta?: { content?: string }; index?: number }[];
            };

            if (parsed.id) {
              lastMessageId = parsed.id;
            }

            const content = parsed.choices?.[0]?.delta?.content;
            if (content !== undefined && content !== null) {
              this.resetTimeout(options);
              options.onToken(content, lastMessageId);
            }
          } catch {
            // Skip malformed JSON lines
          }
        }
      }
    } catch (err: unknown) {
      if ((err as DOMException)?.name === 'AbortError') return;
      this.clearTimeout();
      options.onError({ code: 'STREAM_ERROR', message: String(err) });
    } finally {
      this.clearTimeout();
    }
  }
}
