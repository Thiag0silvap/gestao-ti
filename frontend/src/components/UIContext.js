import { createContext, useContext } from "react";

export const UIContext = createContext(null);

export function useUI() {
  const context = useContext(UIContext);

  if (!context) {
    throw new Error("useUI must be used within UIProvider");
  }

  return context;
}
