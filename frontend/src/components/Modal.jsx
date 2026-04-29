import { useEffect } from "react";
import { X } from "@phosphor-icons/react";

/**
 * Lightweight modal that pins to top of viewport (with comfortable padding)
 * so the user never has to scroll a long page to find it. Also locks scroll.
 */
export default function Modal({ onClose, title, children, testid, maxWidth = "max-w-md" }) {
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e) => { if (e.key === "Escape") onClose?.(); };
    window.addEventListener("keydown", onKey);
    return () => { document.body.style.overflow = prev; window.removeEventListener("keydown", onKey); };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-[60] bg-[#0A1628]/85 backdrop-blur-sm overflow-y-auto"
      onClick={onClose}
      data-testid={testid || "modal-backdrop"}
    >
      {/* Pin to top with breathing room — predictable position regardless of page scroll */}
      <div className="min-h-full flex items-start justify-center pt-16 pb-10 px-4">
        <div
          onClick={(e) => e.stopPropagation()}
          className={`helix-card w-full ${maxWidth} fade-up shadow-2xl`}
          role="dialog"
          aria-modal="true"
        >
          <div className="flex items-center justify-between px-6 py-4 border-b border-[#1A7A6E]/20">
            <div className="helix-h3">{title}</div>
            <button onClick={onClose} className="text-[#9CA3AF] hover:text-[#F5F5F5]" aria-label="Close" data-testid="modal-close"><X size={18}/></button>
          </div>
          <div className="p-6">{children}</div>
        </div>
      </div>
    </div>
  );
}
