/** @type {import('tailwindcss').Config} */
export default {
  content: [
    // アプリケーションのエントリーポイント
    "./index.html",
    // すべてのReactコンポーネント（.js, .jsx, .ts, .tsx）
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
