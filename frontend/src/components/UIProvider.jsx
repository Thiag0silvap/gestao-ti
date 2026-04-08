import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";

const UIContext = createContext(null);

function UIProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const [confirmState, setConfirmState] = useState(null);
  const confirmResolverRef = useRef(null);

  const dismissToast = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const notify = useCallback((message, type = "info") => {
    const id = crypto.randomUUID();
    setToasts((current) => [...current, { id, message, type }]);

    window.setTimeout(() => {
      dismissToast(id);
    }, 4200);
  }, [dismissToast]);

  const confirm = useCallback((options) => {
    return new Promise((resolve) => {
      confirmResolverRef.current = resolve;
      setConfirmState({
        title: options.title || "Confirmar acao",
        message: options.message || "Deseja continuar?",
        confirmLabel: options.confirmLabel || "Confirmar",
        cancelLabel: options.cancelLabel || "Cancelar",
        tone: options.tone || "default",
      });
    });
  }, []);

  const closeConfirm = useCallback((result) => {
    if (confirmResolverRef.current) {
      confirmResolverRef.current(result);
      confirmResolverRef.current = null;
    }
    setConfirmState(null);
  }, []);

  const value = useMemo(() => ({ notify, confirm }), [notify, confirm]);

  return (
    <UIContext.Provider value={value}>
      {children}

      <div className="pointer-events-none fixed right-4 top-4 z-[90] flex w-[min(92vw,380px)] flex-col gap-3">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto rounded-[22px] border px-4 py-4 shadow-xl backdrop-blur-md transition ${
              toast.type === "success"
                ? "border-emerald-200 bg-emerald-50/95 text-emerald-900"
                : toast.type === "error"
                  ? "border-rose-200 bg-rose-50/95 text-rose-900"
                  : "border-slate-200 bg-white/95 text-slate-900"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm leading-6">{toast.message}</p>
              <button
                type="button"
                onClick={() => dismissToast(toast.id)}
                className="rounded-full px-2 py-1 text-xs text-slate-500 transition hover:bg-black/5 hover:text-slate-800"
              >
                fechar
              </button>
            </div>
          </div>
        ))}
      </div>

      {confirmState && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/40 px-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-[30px] border border-white/40 bg-white/92 p-6 shadow-[0_24px_70px_rgba(15,23,42,0.24)]">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Confirmacao</p>
            <h3 className="mt-3 font-[var(--font-display)] text-3xl font-semibold text-slate-900">
              {confirmState.title}
            </h3>
            <p className="mt-4 text-sm leading-6 text-slate-600">{confirmState.message}</p>

            <div className="mt-6 flex flex-wrap gap-3">
              <button type="button" onClick={() => closeConfirm(false)} className="btn-secondary">
                {confirmState.cancelLabel}
              </button>
              <button
                type="button"
                onClick={() => closeConfirm(true)}
                className={confirmState.tone === "danger" ? "btn-danger" : "btn-primary"}
              >
                {confirmState.confirmLabel}
              </button>
            </div>
          </div>
        </div>
      )}
    </UIContext.Provider>
  );
}

export function useUI() {
  const context = useContext(UIContext);

  if (!context) {
    throw new Error("useUI must be used within UIProvider");
  }

  return context;
}

export default UIProvider;
