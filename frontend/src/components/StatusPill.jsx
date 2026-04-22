export function StatusPill({ status }) {
  const val = String(status || "").toLowerCase();
  const map = {
    approved: "helix-status-ok",
    active: "helix-status-ok",
    confirmed: "helix-status-ok",
    completed: "helix-status-ok",
    delivered: "helix-status-ok",
    under_review: "helix-status-warn",
    pending: "helix-status-warn",
    expiring_soon: "helix-status-warn",
    draft: "helix-status-neutral",
    in_production: "helix-status-warn",
    ready_to_ship: "helix-status-warn",
    shipped: "helix-status-warn",
    rejected: "helix-status-danger",
    expired: "helix-status-danger",
    failed: "helix-status-danger",
    disputed: "helix-status-danger",
    paid: "helix-status-gold",
    received: "helix-status-gold",
  };
  const cls = map[val] || "helix-status-neutral";
  const label = val.replace(/_/g, " ");
  return <span className={`helix-status ${cls}`} data-testid={`status-${val}`}>{label}</span>;
}
