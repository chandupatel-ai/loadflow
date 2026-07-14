import axios from "axios";

// Set VITE_API_URL in your deployment env (e.g. Vercel/Netlify) to point
// at the deployed FastAPI backend. Falls back to localhost for dev.
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("loadflow_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;
export { API_URL };
