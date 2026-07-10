import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "summary",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

interface Props {
  open: boolean;
  onClose: () => void;
  titleId: string;
  className: string;
  overlayClassName: string;
  children: ReactNode;
  /** All current desk overlays are safe to dismiss without mutating state. */
  closeOnEscape?: boolean;
}

/**
 * Shared modal behavior for the desk's document viewer, guide, and Case File.
 * The surface is portalled outside #root so the entire application can be made
 * inert and hidden from assistive technology while the dialog is active.
 */
export default function AccessibleDialog({
  open,
  onClose,
  titleId,
  className,
  overlayClassName,
  children,
  closeOnEscape = true,
}: Props) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;

    openerRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;

    const appRoot = document.getElementById("root");
    const previousInert = appRoot?.inert ?? false;
    const previousAriaHidden = appRoot?.getAttribute("aria-hidden");
    const previousOverflow = document.body.style.overflow;

    if (appRoot) {
      appRoot.inert = true;
      appRoot.setAttribute("aria-hidden", "true");
    }
    document.body.style.overflow = "hidden";
    dialogRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && closeOnEscape) {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;

      const dialog = dialogRef.current;
      if (!dialog) return;
      const focusable = [...dialog.querySelectorAll<HTMLElement>(FOCUSABLE)];
      if (focusable.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    const onFocusIn = (event: FocusEvent) => {
      const dialog = dialogRef.current;
      if (dialog && !dialog.contains(event.target as Node)) dialog.focus();
    };

    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("focusin", onFocusIn);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("focusin", onFocusIn);
      if (appRoot) {
        appRoot.inert = previousInert;
        if (previousAriaHidden == null) appRoot.removeAttribute("aria-hidden");
        else appRoot.setAttribute("aria-hidden", previousAriaHidden);
      }
      document.body.style.overflow = previousOverflow;
      const opener = openerRef.current;
      if (opener?.isConnected) opener.focus();
    };
  }, [closeOnEscape, onClose, open]);

  if (!open) return null;

  return createPortal(
    <div
      className={overlayClassName}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        className={className}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}
