// ─── HTTP Error Code → User Message ────────────────────────────

export const ERROR_MAP: Record<number, string> = {
  401: '登录已过期，请重新登录',
  404: '请求的资源不存在',
  409: 'AI 正在处理上一条消息，请稍候',
  413: '文件过大（最大 200MB）',
  415: '不支持该文件格式',
  429: '请求过于频繁，请稍后重试',
  500: '服务器内部错误，请稍后重试',
  503: '系统繁忙，请稍后重试',
};

// ─── SSE Error Code → User Message ─────────────────────────────

export const SSE_ERROR_MAP: Record<string, string> = {
  CONCURRENT_REQUEST: 'AI 正在处理上一条消息，请稍候',
  STREAM_TIMEOUT: '消息发送中断，请重试',
  NETWORK_ERROR: '网络连接失败，请检查网络',
  HTTP_ERROR: '服务器错误，请稍后重试',
  NO_BODY: '服务器响应异常',
  STREAM_ERROR: '消息接收中断，请重试',
};

// ─── WebSocket Close Code → Handling ───────────────────────────

export const WS_CLOSE_MAP: Record<number, { message: string; shouldReconnect: boolean }> = {
  1000: { message: '', shouldReconnect: false },
  1006: { message: '连接异常断开', shouldReconnect: true },
  4001: { message: '连接被拒绝：缺少租户信息', shouldReconnect: false },
};
