import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth-context";

export default function AuthCallback() {
  const nav = useNavigate();
  const { setUser } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const hash = window.location.hash || "";
    const match = hash.match(/session_id=([^&]+)/);
    if (!match) { nav("/login"); return; }
    const session_id = decodeURIComponent(match[1]);
    (async () => {
      try {
        const { data } = await api.post("/auth/emergent/session", { session_id });
        if (data.session_token) localStorage.setItem("helix_token", data.session_token);
        setUser(data.user);
        window.history.replaceState(null, "", "/dashboard");
        nav("/dashboard", { replace: true });
      } catch {
        nav("/login", { replace: true });
      }
    })();
  }, [nav, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A1628]">
      <div className="text-[#C9922A] font-mono tracking-widest text-xs animate-pulse">
        ESTABLISHING SESSION…
      </div>
    </div>
  );
}
