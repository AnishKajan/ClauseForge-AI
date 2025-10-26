const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',            // enables static export
  images: { unoptimized: true },
  trailingSlash: true,
  
  webpack: (config, { isServer }) => {
    // Map "@" to "<project>/src" for both TS and Webpack
    const srcPath = path.resolve(__dirname, "src");
    
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      "@": srcPath,
    };
    
    return config;
  },
  
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY,
  },
};

module.exports = nextConfig;