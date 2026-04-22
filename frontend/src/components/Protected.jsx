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
  if (roles && !roles.includes(user.role)) {
    // consumers don't have a business dashboard — send them to shop
    if (user.role === "consumer") return <Navigate to="/shop" replace />;
    if (user.role === "jompstart_admin") return <Navigate to="/admin/credit" replace />;
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}
