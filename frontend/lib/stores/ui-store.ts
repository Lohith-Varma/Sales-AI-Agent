"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIState {
  sidebarCollapsed: boolean;
  commandOpen: boolean;
  density: "comfortable" | "compact";
  reduceDataMotion: boolean;
  showConfidence: boolean;
  autoOpenReferences: boolean;
  transcriptBookmarks: Record<string, string[]>;
  callNotes: Record<string, string>;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setCommandOpen: (open: boolean) => void;
  setDensity: (density: UIState["density"]) => void;
  setReduceDataMotion: (enabled: boolean) => void;
  setShowConfidence: (enabled: boolean) => void;
  setAutoOpenReferences: (enabled: boolean) => void;
  toggleBookmark: (callId: string, segmentId: string) => void;
  setCallNote: (callId: string, note: string) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      commandOpen: false,
      density: "comfortable",
      reduceDataMotion: false,
      showConfidence: true,
      autoOpenReferences: true,
      transcriptBookmarks: {},
      callNotes: {},
      setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
      setCommandOpen: (commandOpen) => set({ commandOpen }),
      setDensity: (density) => set({ density }),
      setReduceDataMotion: (reduceDataMotion) => set({ reduceDataMotion }),
      setShowConfidence: (showConfidence) => set({ showConfidence }),
      setAutoOpenReferences: (autoOpenReferences) => set({ autoOpenReferences }),
      toggleBookmark: (callId, segmentId) => set((state) => {
        const existing = state.transcriptBookmarks[callId] ?? [];
        const next = existing.includes(segmentId) ? existing.filter((id) => id !== segmentId) : [...existing, segmentId];
        return { transcriptBookmarks: { ...state.transcriptBookmarks, [callId]: next } };
      }),
      setCallNote: (callId, note) => set((state) => ({ callNotes: { ...state.callNotes, [callId]: note } })),
    }),
    { name: "payin3.workspace.v1", partialize: ({ sidebarCollapsed, density, reduceDataMotion, showConfidence, autoOpenReferences, transcriptBookmarks, callNotes }) => ({ sidebarCollapsed, density, reduceDataMotion, showConfidence, autoOpenReferences, transcriptBookmarks, callNotes }) },
  ),
);
