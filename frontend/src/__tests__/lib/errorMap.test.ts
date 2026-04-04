import { ERROR_MAP } from '../../lib/errorMap';

describe('ERROR_MAP', () => {
  it('maps 401 to login expired message', () => {
    expect(ERROR_MAP[401]).toBe('登录已过期，请重新登录');
  });

  it('maps 409 to AI processing message', () => {
    expect(ERROR_MAP[409]).toBe('AI 正在处理上一条消息，请稍候');
  });

  it('maps 415 to unsupported format message', () => {
    expect(ERROR_MAP[415]).toBe('不支持该文件格式');
  });

  it('maps 429 to rate limit message', () => {
    expect(ERROR_MAP[429]).toBe('请求过于频繁，请稍后重试');
  });

  it('maps 500 to server error message', () => {
    expect(ERROR_MAP[500]).toBe('服务器内部错误，请稍后重试');
  });

  it('maps 503 to system busy message', () => {
    expect(ERROR_MAP[503]).toBe('系统繁忙，请稍后重试');
  });

  it('maps 404 to not found message', () => {
    expect(ERROR_MAP[404]).toBe('请求的资源不存在');
  });

  it('maps 413 to file too large message', () => {
    expect(ERROR_MAP[413]).toBe('文件过大（最大 50MB）');
  });

  it('returns undefined for unknown status codes', () => {
    expect(ERROR_MAP[418]).toBeUndefined();
    expect(ERROR_MAP[502]).toBeUndefined();
  });
});
