import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth-context";
import { Handbag, SignOut, UserCircle, CaretDown } from "@phosphor-icons/react";
import { useState } from "react";
import ThemeToggle from "./ThemeToggle";

/** Top-bar shell for the consumer-facing storefront (now the main app surface). */
export default function ShopShell({ children }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const dashHome = user?.role === "consumer" ? "/shop/orders"
    : user?.role === "jompstart_admin" ? "/admin/credit"
    : user ? "/dashboard" : null;

  return (
    <div className="min-h-screen bg-[#0A1628] text-[#F5F5F5]">
      <header className="sticky top-0 z-30 bg-[#0A1628]/95 backdrop-blur border-b border-[#1A7A6E]/20">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-4 flex items-center justify-between gap-6">
          <Link to="/" className="flex items-center gap-3" data-testid="shop-home-link">
            <img src="/jomp-icon.png" alt="Jomp" className="w-9 h-9 rounded-full"/>
            <div className="leading-tight">
              <div className="font-bold tracking-[0.22em] text-sm">JOMP SHOP</div>
              <div className="text-[9px] tracking-[0.3em] text-[#1A7A6E] font-mono">DIRECT · FROM AFRICA</div>
            </div>
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-[13px] text-[#9CA3AF]">
            <Link to="/" className="hover:text-[#F5F5F5]" data-testid="nav-shop">Shop</Link>
            <Link to="/?mode=riby_dtc" className="hover:text-[#F5F5F5]" data-testid="nav-direct">Direct from Africa</Link>
            <Link to="/?mode=buyer_local" className="hover:text-[#F5F5F5]" data-testid="nav-instock">US In-Stock</Link>
            <Link to="/about" className="hover:text-[#F5F5F5]" data-testid="nav-about">About</Link>
            <Link to="/register?role=exporter" className="hover:text-[#F5F5F5]" data-testid="nav-sell">Become a Seller</Link>
            {user && <Link to="/shop/orders" className="hover:text-[#F5F5F5]" data-testid="my-orders-link"><Handbag size={14} className="inline mr-1"/>My Orders</Link>}
          </nav>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            {user ? (
              <div className="relative">
                <button onClick={()=>setMenuOpen(o=>!o)} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[#1A7A6E]/30 text-[12px] hover:border-[#C9922A]/50" data-testid="user-menu-trigger">
                  <UserCircle size={14}/> {user.name.split(" ")[0]} <CaretDown size={10}/>
                </button>
                {menuOpen && (
                  <div className="absolute right-0 mt-2 w-56 helix-card p-2 shadow-2xl z-40" onMouseLeave={()=>setMenuOpen(false)}>
                    <div className="px-3 py-2 border-b border-[#1A7A6E]/20 mb-1">
                      <div className="text-[12px] font-semibold truncate">{user.name}</div>
                      <div className="text-[10px] font-mono uppercase tracking-wider text-[#1A7A6E]">{user.role.replace("_"," ")}</div>
                    </div>
                    {dashHome && <Link to={dashHome} className="block px-3 py-2 text-[12px] hover:bg-[#1A7A6E]/10 rounded" data-testid="user-menu-dashboard">{user.role === "consumer" ? "My Orders" : "Dashboard"}</Link>}
                    {(user.role === "exporter" || user.role === "buyer") && (
                      <Link to="/dashboard" className="block px-3 py-2 text-[12px] hover:bg-[#1A7A6E]/10 rounded">Business workspace</Link>
                    )}
                    <button onClick={async () => { await logout(); nav("/"); }} className="w-full text-left px-3 py-2 text-[12px] text-[#E74C3C] hover:bg-[#E74C3C]/10 rounded inline-flex items-center gap-2" data-testid="shop-logout">
                      <SignOut size={12}/> Sign out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <>
                <Link to="/login" className="text-[13px] text-[#9CA3AF] hover:text-[#F5F5F5]" data-testid="header-signin">Sign in</Link>
                <Link to="/register" className="helix-btn-primary text-sm inline-flex items-center gap-1" data-testid="header-signup"><UserCircle size={14}/> Sign up</Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="max-w-[1400px] mx-auto px-6 lg:px-10 py-8 fade-up">{children}</main>
      <footer className="border-t border-[#1A7A6E]/15 py-10 mt-16">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 grid md:grid-cols-4 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <img src="/jomp-icon.png" alt="" className="w-7 h-7 rounded-full"/>
              <span className="font-bold tracking-[0.22em] text-sm">JOMP SHOP</span>
            </div>
            <p className="text-[12px] text-[#9CA3AF] leading-relaxed">Africa's direct-to-shopper marketplace. Buy direct from verified makers. Escrow-protected by Riby Inc.</p>
          </div>
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-[#1A7A6E] mb-3">Shop</div>
            <ul className="space-y-2 text-[12px] text-[#9CA3AF]">
              <li><Link to="/?category=fashion" className="hover:text-[#F5F5F5]">Fashion &amp; Textiles</Link></li>
              <li><Link to="/?category=staple-foods" className="hover:text-[#F5F5F5]">Staple Foods</Link></li>
              <li><Link to="/?category=beauty" className="hover:text-[#F5F5F5]">Beauty &amp; Cosmetics</Link></li>
              <li><Link to="/?category=home-decor" className="hover:text-[#F5F5F5]">Home &amp; Decor</Link></li>
              <li><Link to="/?category=accessories" className="hover:text-[#F5F5F5]">Accessories</Link></li>
            </ul>
          </div>
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-[#1A7A6E] mb-3">Sellers</div>
            <ul className="space-y-2 text-[12px] text-[#9CA3AF]">
              <li><Link to="/register?role=exporter" className="hover:text-[#F5F5F5]">Become an exporter</Link></li>
              <li><Link to="/register?role=buyer" className="hover:text-[#F5F5F5]">Become a reseller / importer</Link></li>
              <li><Link to="/about" className="hover:text-[#F5F5F5]">For African brands</Link></li>
              <li><Link to="/about#modules" className="hover:text-[#F5F5F5]">Trade platform</Link></li>
            </ul>
          </div>
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-[#1A7A6E] mb-3">Company</div>
            <ul className="space-y-2 text-[12px] text-[#9CA3AF]">
              <li><Link to="/about" className="hover:text-[#F5F5F5]">About Jomp Shop</Link></li>
              <li><Link to="/about#partners" className="hover:text-[#F5F5F5]">Partners</Link></li>
              <li><Link to="/login" className="hover:text-[#F5F5F5]">Sign in</Link></li>
              <li><Link to="/register" className="hover:text-[#F5F5F5]">Create account</Link></li>
            </ul>
          </div>
        </div>
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 mt-8 pt-6 border-t border-[#1A7A6E]/15 text-center">
          <div className="text-[11px] text-[#1A7A6E] font-mono tracking-widest flex flex-wrap justify-center gap-x-3 gap-y-1">
            <span>JOMP SHOP · POWERED BY</span><span>·</span><span>RIBY INC</span><span>·</span><span>JOMPSTART DIGITAL</span><span>·</span><span>ANCHOR</span>
          </div>
          <div className="text-[10px] text-[#9CA3AF] mt-2">© 2026 Jomp Shop. Africa to the world.</div>
        </div>
      </footer>
    </div>
  );
}
