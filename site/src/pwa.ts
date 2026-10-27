import { useEffect, useState } from "preact/hooks";
import { registerSW } from "virtual:pwa-register";

/**
 * Service worker state. The worker precaches the app and all terms on the
 * first visit; after that TermQuake opens and searches with no connection.
 */
export interface PwaState {
  offlineReady: boolean;
  needRefresh: boolean;
}

let state: PwaState = { offlineReady: false, needRefresh: false };
const listeners = new Set<(s: PwaState) => void>();
let updateSW: ((reloadPage?: boolean) => Promise<void>) | undefined;

function set(patch: Partial<PwaState>) {
  state = { ...state, ...patch };
  listeners.forEach((fn) => fn(state));
}

export function initPwa(): void {
  if (!("serviceWorker" in navigator)) return;
  // Already controlled by a worker from an earlier visit: content is cached.
  if (navigator.serviceWorker.controller) set({ offlineReady: true });
  updateSW = registerSW({
    immediate: true,
    onOfflineReady: () => set({ offlineReady: true }),
    onNeedRefresh: () => set({ needRefresh: true }),
  });
}

export function applyUpdate(): void {
  void updateSW?.(true);
}

export function usePwa(): PwaState {
  const [current, setCurrent] = useState(state);
  useEffect(() => {
    listeners.add(setCurrent);
    return () => void listeners.delete(setCurrent);
  }, []);
  return current;
}

export function useOnline(): boolean {
  const [online, setOnline] = useState(typeof navigator === "undefined" ? true : navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  return online;
}
