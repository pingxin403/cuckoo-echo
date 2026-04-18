import { useEffect, useRef, useCallback, useState } from 'react';
import { SSEClient } from '@/network/sseClient';
import type { ConnectionStatus, SSEError } from '@/types';

interface UseSSEOptions {
  url: string;
  apiKey: string;
  onToken?: (token: string, messageId?: string) => void;
  onDone?: (messageId: string) => void;
  onError?: (error: SSEError) => void;
  onReconnected?: () => void;
}

interface UseSSEReturn {
  send: (body: object) => void;
  disconnect: () => void;
  connectionStatus: ConnectionStatus;
}

export function useSSE({
  url,
  apiKey,
  onToken,
  onDone,
  onError,
  onReconnected,
}: UseSSEOptions): UseSSEReturn {
  const clientRef = useRef<SSEClient | null>(null);
  const callbacksRef = useRef({ onToken, onDone, onError, onReconnected });
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>('disconnected');
  const wasDisconnectedRef = useRef(false);

  useEffect(() => {
    callbacksRef.current = { onToken, onDone, onError, onReconnected };
  }, [onToken, onDone, onError, onReconnected]);

  useEffect(() => {
    const client = new SSEClient();
    clientRef.current = client;
    return () => {
      client.disconnect();
      clientRef.current = null;
      setConnectionStatus('disconnected');
    };
  }, [url, apiKey]);

  const send = useCallback(
    (body: object) => {
      const client = clientRef.current;
      if (!client || !url || !apiKey) return;
      setConnectionStatus('connecting');
      client
        .connect({
          url,
          body,
          apiKey,
          onToken(token: string, messageId?: string) {
            const wasDisconnected = wasDisconnectedRef.current;
            setConnectionStatus('connected');
            wasDisconnectedRef.current = false;
            // Fire onReconnected when transitioning from disconnected → connected
            if (wasDisconnected) {
              callbacksRef.current.onReconnected?.();
            }
            callbacksRef.current.onToken?.(token, messageId);
          },
          onDone(messageId: string) {
            setConnectionStatus('connected');
            callbacksRef.current.onDone?.(messageId);
          },
          onError(error: SSEError) {
            wasDisconnectedRef.current = true;
            setConnectionStatus('disconnected');
            callbacksRef.current.onError?.(error);
          },
        })
        .catch(() => {
          setConnectionStatus('disconnected');
        });
    },
    [url, apiKey],
  );

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect();
    setConnectionStatus('disconnected');
  }, []);

  return { send, disconnect, connectionStatus };
}
