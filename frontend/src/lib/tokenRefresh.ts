import axios from 'axios';

let refreshPromise: Promise<string | null> | null = null;

// Callback setters for AuthStore integration (set when store is ready)
let setAccessToken: (token: string) => void = () => {};
let logout: () => void = () => {};

export function setAuthCallbacks(
  setToken: (token: string) => void,
  logoutFn: () => void,
): void {
  setAccessToken = setToken;
  logout = logoutFn;
}

export async function refreshTokenWithMutex(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const res = await axios.post<{ access_token: string }>(
        '/admin/v1/auth/refresh',
        null,
        { withCredentials: true },
      );
      const newToken = res.data.access_token;
      setAccessToken(newToken);
      return newToken;
    } catch {
      logout();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}
