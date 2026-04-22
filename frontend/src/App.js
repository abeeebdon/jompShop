import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "./lib/auth-context";
import Protected from "./components/Protected";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import AuthCallback from "./pages/AuthCallback";
import Dashboard from "./pages/Dashboard";
import Onboarding from "./pages/Onboarding";
import Catalog from "./pages/Catalog";
import ProductDetail from "./pages/ProductDetail";
import MyProducts from "./pages/MyProducts";
import Orders from "./pages/Orders";
import OrderDetail from "./pages/OrderDetail";
import Compliance from "./pages/Compliance";
import Finance from "./pages/Finance";
import AdminOverview from "./pages/AdminOverview";
import AdminVerifications from "./pages/AdminVerifications";
import AdminDisputes from "./pages/AdminDisputes";

function AppRouter() {
  const loc = useLocation();
  // Handle OAuth callback synchronously during render (not in useEffect)
  if (loc.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
      <Route path="/onboarding" element={<Protected><Onboarding /></Protected>} />
      <Route path="/catalog" element={<Protected><Catalog /></Protected>} />
      <Route path="/products/:id" element={<Protected><ProductDetail /></Protected>} />
      <Route path="/my-products" element={<Protected roles={["exporter"]}><MyProducts /></Protected>} />
      <Route path="/orders" element={<Protected><Orders /></Protected>} />
      <Route path="/orders/:id" element={<Protected><OrderDetail /></Protected>} />
      <Route path="/compliance" element={<Protected><Compliance /></Protected>} />
      <Route path="/finance" element={<Protected><Finance /></Protected>} />
      <Route path="/admin" element={<Protected roles={["admin", "super_admin"]}><AdminOverview /></Protected>} />
      <Route path="/admin/verifications" element={<Protected roles={["admin", "super_admin"]}><AdminVerifications /></Protected>} />
      <Route path="/admin/disputes" element={<Protected roles={["admin", "super_admin"]}><AdminDisputes /></Protected>} />
      <Route path="/admin/finance" element={<Protected roles={["admin", "super_admin"]}><AdminOverview /></Protected>} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster
            position="top-right"
            theme="dark"
            toastOptions={{
              style: { background: "#0F2040", color: "#F5F5F5", border: "1px solid rgba(26,122,110,0.3)" },
            }}
          />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}
export default App;
