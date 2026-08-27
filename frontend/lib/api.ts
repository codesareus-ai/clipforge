// Thin client for the ClipForge backend. Stores the bearer token in
// localStorage and attaches it to every authenticated request.
const TOKEN_KEY = "clipforge_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function authedFetch(path: string, init: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body) headers.set("Content-Type", "application/json");
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401) {
    // Token missing/invalid — drop it so the UI returns to the login form.
    clearToken();
  }
  return res;
}

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export const api = {
  async register(handle: string, password: string) {
    const r = await fetch(`${BACKEND}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ handle, password }),
    });
    return r.json();
  },
  async login(handle: string, password: string) {
    const r = await fetch(`${BACKEND}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ handle, password }),
    });
    return r.json();
  },
  async logout() {
    const r = await authedFetch(`${BACKEND}/auth/logout`, { method: "POST" });
    clearToken();
    return r.json().catch(() => ({ ok: true }));
  },
  async createJob(url: string, top_n: number, platforms: string[]) {
    const r = await authedFetch(`${BACKEND}/jobs`, {
      method: "POST",
      body: JSON.stringify({ url, top_n, platforms }),
    });
    return r.json();
  },
  async getJob(id: string) {
    const r = await authedFetch(`${BACKEND}/jobs/${id}`);
    return r.json();
  },
};
