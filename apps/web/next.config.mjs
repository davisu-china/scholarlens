/** @type {import('next').NextConfig} */
const API = process.env.SL_API_URL || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    // 前端 /api/* 代理到 FastAPI，开发时避免 CORS。后端不在本机 8000 端口时设置 SL_API_URL。
    return [{ source: "/api/:path*", destination: `${API}/:path*` }];
  },
};
export default nextConfig;
