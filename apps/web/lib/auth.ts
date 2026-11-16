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
