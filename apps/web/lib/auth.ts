"use client";

const TOKEN = "sl_token";
const USER = "sl_user";
const LAST_USER = "sl_last_user";  // 退出后仍保留，用来判断是否换了账号
const STORE = "scholarlens";      // zustand 持久化的 key（见 store/app.ts）

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export function getToken(): string | null {
  return typeof window === "undefined" ? null : localStorage.getItem(TOKEN);
}

export function getUsername(): string | null {
  return typeof window === "undefined" ? null : localStorage.getItem(USER);
}

/** 把后端的错误响应读成一句人能看懂的话。 */
export async function readError(r: Response): Promise<ApiError> {
  let msg = "";
  try {
    const body = await r.clone().json();
    msg = typeof body?.detail === "string" ? body.detail : JSON.stringify(body?.detail ?? body);
  } catch {
    msg = await r.text().catch(() => "");
  }
  return new ApiError(r.status, msg || `请求失败（${r.status}）`);
}

export async function signIn(mode: "login" | "register", username: string, password: string): Promise<void> {
  const r = await fetch(`/api/auth/${mode}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) {
    if (r.status === 401) throw new ApiError(401, "用户名或密码不正确");
    if (r.status === 409) throw new ApiError(409, "这个用户名已被注册，可以直接登录");
    if (r.status >= 500) throw new ApiError(r.status, "服务暂时不可用，请稍后再试");
    throw await readError(r);
  }
  const { access_token } = await r.json();
  // 对话记录存在本机：换了账号就清掉上一个人的，避免串号
  if (localStorage.getItem(LAST_USER) !== username) {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE) || "null");
      if (saved?.state) {
        saved.state = { ...saved.state, sessions: [], currentId: null, collection: null, model: null };
        localStorage.setItem(STORE, JSON.stringify(saved));
      }
    } catch { localStorage.removeItem(STORE); }
  }
  localStorage.setItem(LAST_USER, username);
  localStorage.setItem(TOKEN, access_token);
  localStorage.setItem(USER, username);
}

export function signOut(redirect = true) {
  localStorage.removeItem(TOKEN);
  localStorage.removeItem(USER);
  if (redirect && typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    window.location.href = "/login";
  }
}

/** 带鉴权的 fetch。登录失效时回到登录页。 */
export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  if (!token) {
    signOut();
    throw new ApiError(401, "请先登录");
  }
  let r: Response;
  try {
    r = await fetch(input, { ...init, headers: { ...init.headers, Authorization: `Bearer ${token}` } });
  } catch (e) {
    if ((e as Error)?.name === "AbortError") throw e;
    throw new ApiError(0, "网络连接失败，请检查网络或确认服务已启动");
  }
  if (r.status === 401) {
    signOut();
    throw new ApiError(401, "登录已过期，请重新登录");
  }
  return r;
}
