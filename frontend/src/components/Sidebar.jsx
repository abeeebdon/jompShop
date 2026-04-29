import { NavLink, useNavigate } from "react-router-dom";
import {
  HouseSimple, Package, Receipt, ShieldCheck, Wallet, Users,
  SignOut, ArrowsClockwise, CaretRight, Storefront, FileText, CurrencyCircleDollar, Gauge, HandCoins,
  Truck, ShoppingCart,
} from "@phosphor-icons/react";
import { useAuth } from "../lib/auth-context";

const NAV = {
  exporter: [
    { to: "/dashboard", label: "Command Center", icon: Gauge },
    { to: "/my-products", label: "My Products", icon: Package },
    { to: "/catalog", label: "Marketplace", icon: Storefront },
    { to: "/orders", label: "Orders", icon: Receipt },
    { to: "/sell", label: "Sell Direct (DTC)", icon: Truck },
    { to: "/fulfillment", label: "Fulfillment", icon: ShoppingCart },
    { to: "/compliance", label: "Compliance", icon: ShieldCheck },
    { to: "/finance", label: "Finance", icon: Wallet },
    { to: "/finance/accounts", label: "Withdrawal Accounts", icon: HandCoins },
    { to: "/credit", label: "Business Credit", icon: HandCoins },
    { to: "/repayment", label: "Repayments", icon: ArrowsClockwise },
    { to: "/onboarding", label: "Business Profile", icon: FileText },
  ],
  buyer: [
    { to: "/dashboard", label: "Command Center", icon: Gauge },
    { to: "/catalog", label: "Marketplace", icon: Storefront },
    { to: "/orders", label: "My Orders", icon: Receipt },
    { to: "/sell", label: "Local Inventory Shop", icon: ShoppingCart },
    { to: "/fulfillment", label: "Fulfillment", icon: Truck },
    { to: "/finance", label: "Finance", icon: Wallet },
    { to: "/finance/accounts", label: "Withdrawal Accounts", icon: HandCoins },
    { to: "/onboarding", label: "Business Profile", icon: FileText },
  ],
  admin: [
    { to: "/admin", label: "Admin Overview", icon: Gauge },
    { to: "/admin/verifications", label: "Verifications", icon: ShieldCheck },
    { to: "/admin/credit", label: "JompStart Credit", icon: HandCoins },
    { to: "/admin/disputes", label: "Disputes", icon: ArrowsClockwise },
    { to: "/admin/finance", label: "Financial Overview", icon: CurrencyCircleDollar },
    { to: "/catalog", label: "Marketplace", icon: Storefront },
  ],
  jompstart_admin: [
    { to: "/admin/credit", label: "JompStart Credit", icon: HandCoins },
  ],
};

NAV.super_admin = NAV.admin;

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const items = NAV[user?.role] || NAV.exporter;

  return (
    <aside className="fixed left-0 top-0 h-screen w-16 lg:w-60 bg-[#0A1628] border-r border-[#1A7A6E]/20 flex flex-col z-40">
      <div className="px-4 lg:px-6 py-5 border-b border-[#1A7A6E]/15 flex items-center gap-2">
        <img src="/jomp-icon.png" alt="Jomp" className="w-8 h-8 rounded-full"/>
        <div className="hidden lg:flex flex-col leading-tight">
          <span className="font-bold tracking-[0.2em] text-[13px]">JOMP SHOP</span>
          <span className="text-[9px] tracking-[0.3em] text-[#1A7A6E] font-mono">EXPORT OS v1.1</span>
        </div>
      </div>

      <nav className="flex-1 py-4 overflow-y-auto">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, "-")}`}
              className={({ isActive }) =>
                `group flex items-center gap-3 px-4 lg:px-6 py-3 border-l-2 transition-colors ${
                  isActive
                    ? "border-[#C9922A] bg-[#C9922A]/6 text-[#C9922A]"
                    : "border-transparent text-[#9CA3AF] hover:text-[#F5F5F5] hover:bg-[#1A7A6E]/8"
                }`
              }
            >
              <Icon size={18} weight={"regular"} />
              <span className="hidden lg:block text-[13px] font-medium tracking-wide">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="border-t border-[#1A7A6E]/15 px-3 lg:px-4 py-3">
        <div className="hidden lg:flex items-center gap-2 mb-3 px-2">
          <div className="w-8 h-8 rounded-full bg-[#C9922A]/20 border border-[#C9922A]/40 flex items-center justify-center text-[#C9922A] font-bold text-xs">
            {user?.name?.[0] || "H"}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[12px] font-medium truncate">{user?.name}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-[#1A7A6E]">{user?.role}</div>
          </div>
        </div>
        <button
          data-testid="logout-btn"
          onClick={async () => { await logout(); navigate("/"); }}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-[#9CA3AF] hover:text-[#F5F5F5] hover:bg-[#1A7A6E]/10 text-[12px] transition-colors"
        >
          <SignOut size={16} />
          <span className="hidden lg:inline">Sign out</span>
        </button>
      </div>
    </aside>
  );
}
