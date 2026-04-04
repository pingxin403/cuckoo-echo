import { vi } from 'vitest';
import axios from 'axios';
import { refreshTokenWithMutex, setAuthCallbacks } from '../../lib/tokenRefresh';

vi.mock('axios');
const mockedAxios = vi.mocked(axios, true);

describe('refreshTokenWithMutex', () => {
  let setTokenSpy: ReturnType<typeof vi.fn>;
  let logoutSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    setTokenSpy = vi.fn();
    logoutSpy = vi.fn();
    setAuthCallbacks(setTokenSpy, logoutSpy);
  });

  it('returns new token on successful refresh', async () => {
    mockedAxios.post.mockResolvedValueOnce({
      data: { access_token: 'new-token-123' },
    });

    const token = await refreshTokenWithMutex();

    expect(token).toBe('new-token-123');
    expect(setTokenSpy).toHaveBeenCalledWith('new-token-123');
    expect(mockedAxios.post).toHaveBeenCalledWith(
      '/admin/v1/auth/refresh',
      null,
      { withCredentials: true },
    );
  });

  it('returns null and calls logout on failed refresh', async () => {
    mockedAxios.post.mockRejectedValueOnce(new Error('refresh failed'));

    const token = await refreshTokenWithMutex();

    expect(token).toBeNull();
    expect(logoutSpy).toHaveBeenCalled();
  });

  it('concurrent calls only make one actual request (mutex)', async () => {
    let resolvePost: (value: unknown) => void;
    const postPromise = new Promise((resolve) => {
      resolvePost = resolve;
    });
    mockedAxios.post.mockReturnValueOnce(postPromise as ReturnType<typeof axios.post>);

    // Fire 3 concurrent calls
    const p1 = refreshTokenWithMutex();
    const p2 = refreshTokenWithMutex();
    const p3 = refreshTokenWithMutex();

    // Resolve the single underlying request
    resolvePost!({ data: { access_token: 'shared-token' } });

    const [r1, r2, r3] = await Promise.all([p1, p2, p3]);

    expect(r1).toBe('shared-token');
    expect(r2).toBe('shared-token');
    expect(r3).toBe('shared-token');
    expect(mockedAxios.post).toHaveBeenCalledTimes(1);
  });
});
