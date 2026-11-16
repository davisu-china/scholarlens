"use client";

const KEY = "sl_token";
let inflight: Promise<string> | null = null;

async function login(): Promise<string> {
  // 雏形：自动注册/登录一个 demo 用户。生产换成真实登录页。
  const body = JSON.stringify({ username: "demo", password: "demo-pw" });
  let r = await fetch("/api/auth/register", { method: "POST", headers: { "Content-Type": "application/json" }, body });
  if (r.status === 409) {
    r = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body });
  }
  const { access_token } = await r.json();
  localStorage.setItem(KEY, access_token);
  return access_token;
}

export async function getToken(): Promise<string> {
  const cached = typeof window !== "undefined" ? localStorage.getItem(KEY) : null;
  if (cached) return cached;
  if (!inflight) inflight = login().finally(() => (inflight = null));
  return inflight;
}

export async function authHeaders(): Promise<Record<string, string>> {
  return { Authorization: `Bearer ${await getToken()}` };
}

/** 带鉴权的 fetch：token 失效（401）时丢弃缓存并重新登录一次。 */
export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const send = async () =>
    fetch(input, { ...init, headers: { ...init.headers, ...(await authHeaders()) } });
  let r = await send();
  if (r.status === 401) {
    localStorage.removeItem(KEY);
    r = await send();
  }
  return r;
}
