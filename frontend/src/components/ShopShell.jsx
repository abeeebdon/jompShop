import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth-context";
import { Handbag, SignOut, UserCircle } from "@phosphor-icons/react";

/** Minimal top-bar shell for the consumer shop experience (no left rail). */
export default function ShopShell({ children }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  return (
    <div className="min-h-screen bg-[#0A1628] text-[#F5F5F5]">
      <header className="sticky top-0 z-30 bg-[#0A1628]/95 backdrop-blur border-b border-[#1A7A6E]/20">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-4 flex items-center justify-between gap-6">
          <Link to="/shop" className="flex items-center gap-3" data-testid="shop-home-link">
            <img src="/jomp-favicon.png" alt="Jomp" className="w-9 h-9 rounded-full"/>
            <div className="leading-tight">
              <div className="font-bold tracking-[0.22em] text-sm">JOMP SHOP</div>
              <div className="text-[9px] tracking-[0.3em] text-[#1A7A6E] font-mono">DIRECT · FROM AFRICA</div>
            </div>
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-[13px] text-[#9CA3AF]">
            <Link to="/shop" className="hover:text-[#F5F5F5]">Browse</Link>
            <Link to="/shop?mode=riby_dtc" className="hover:text-[#F5F5F5]">Direct from Africa</Link>
            <Link to="/shop?mode=buyer_local" className="hover:text-[#F5F5F5]">US In-Stock</Link>
            {user && <Link to="/shop/orders" className="hover:text-[#F5F5F5]" data-testid="my-orders-link"><Handbag size={14} className="inline mr-1"/>My Orders</Link>}
          </nav>
          <div className="flex items-center gap-3">
            {user ? (
              <>
                <span className="hidden sm:inline text-[12px] text-[#9CA3AF]">Hi, {user.name.split(" ")[0]}</span>
                {(user.role === "exporter" || user.role === "buyer") && (
                  <Link to="/dashboard" className="text-[12px] text-[#C9922A] hover:underline">Business</Link>
                )}
                <button onClick={async () => { await logout(); nav("/shop"); }} className="text-[#9CA3AF] hover:text-[#F5F5F5]" data-testid="shop-logout"><SignOut size={16}/></button>
              </>
            ) : (
              <Link to="/login" className="helix-btn-primary text-sm inline-flex items-center gap-1" data-testid="shop-login-cta"><UserCircle size={14}/> Sign in</Link>
            )}
          </div>
        </div>
      </header>
      <main className="max-w-[1400px] mx-auto px-6 lg:px-10 py-8 fade-up">{children}</main>
      <footer className="border-t border-[#1A7A6E]/15 py-8 mt-10">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 text-center">
          <div className="text-[12px] text-[#9CA3AF]">Helix Shop — Direct-from-Africa commerce, powered by the Helix Platform.</div>
          <div className="text-[11px] text-[#1A7A6E] font-mono tracking-widest mt-3 flex flex-wrap justify-center gap-x-3 gap-y-1">
            <span>DOBBLEHELIX LIMITED</span><span>·</span><span>RIBY INC</span><span>·</span><span>JOMPSTART DIGITAL</span><span>·</span><span>ANCHOR</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
