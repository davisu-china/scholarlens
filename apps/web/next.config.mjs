/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // 前端 /api/* 代理到 FastAPI，开发时避免 CORS
    return [{ source: "/api/:path*", destination: "http://localhost:8000/:path*" }];
  },
};
export default nextConfig;
