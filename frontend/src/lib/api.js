import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("helix_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const formatUSD = (n) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(n || 0);

export const formatNGN = (n) =>
  new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 }).format(n || 0);

export const formatDate = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return String(iso).slice(0, 10);
  }
};

export const formatDateTime = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return String(iso);
  }
};

export const roleLabel = (r) => ({
  exporter: "Exporter",
  buyer: "Buyer",
  admin: "Admin",
  super_admin: "Super Admin",
}[r] || r);

export const statusClass = (s) => {
  const ok = ["approved", "active", "confirmed", "completed", "delivered", "paid"];
  const warn = ["under_review", "pending", "expiring_soon", "ready_to_ship", "in_production", "shipped", "draft"];
  const danger = ["rejected", "expired", "failed", "disputed"];
  if (ok.includes(s)) return "helix-status helix-status-ok";
  if (warn.includes(s)) return "helix-status helix-status-warn";
  if (danger.includes(s)) return "helix-status helix-status-danger";
  return "helix-status helix-status-neutral";
};
