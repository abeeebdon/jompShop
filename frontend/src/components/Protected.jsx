import { useAuth } from "../lib/auth-context";
import { Navigate } from "react-router-dom";

export default function Protected({ children, roles }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0A1628]">
        <div className="text-[#C9922A] font-mono tracking-widest text-xs animate-pulse">LOADING · HELIX</div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/dashboard" replace />;
  return children;
}
