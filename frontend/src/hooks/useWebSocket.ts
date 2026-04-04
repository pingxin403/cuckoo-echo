import { useEffect, useRef, useCallback, useState } from 'react';
import { WSClient } from '@/network/wsClient';
import type { ConnectionStatus, WSMessage } from '@/types';

interface UseWebSocketOptions {
  url: string;
  onMessage?: (data: WSMessage) => void;
}

interface UseWebSocketReturn {
  send: (data: object) => void;
  disconnect: () => void;
  connectionStatus: ConnectionStatus;
}

export function useWebSocket({ url, onMessage }: UseWebSocketOptions): UseWebSocketReturn {
  const clientRef = useRef<WSClient | null>(null);
  const onMessageRef = useRef(onMessage);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');

  // Keep callback ref up to date without re-triggering effect
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!url) return;

    const client = new WSClient();
    clientRef.current = client;
    setConnectionStatus('connecting');

    client.connect({
      url,
      onMessage(data: WSMessage) {
        onMessageRef.current?.(data);
      },
      onClose() {
        setConnectionStatus('disconnected');
      },
      onError() {
        setConnectionStatus('disconnected');
      },
    });

    setConnectionStatus('connected');

    return () => {
      client.disconnect();
      clientRef.current = null;
      setConnectionStatus('disconnected');
    };
  }, [url]);

  const send = useCallback((data: object) => {
    clientRef.current?.send(data);
  }, []);

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect();
    clientRef.current = null;
    setConnectionStatus('disconnected');
  }, []);

  return { send, disconnect, connectionStatus };
}
