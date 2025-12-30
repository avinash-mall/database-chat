import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UIState, UIConfig } from '@/types';

interface UIStore extends UIState {
    setConfig: (config: UIConfig) => void;
    setTheme: (theme: 'light' | 'dark') => void;
    toggleSidebar: () => void;
    setSidebarCollapsed: (collapsed: boolean) => void;
}

/**
 * Zustand store for UI state
 * Manages theme, sidebar, and config
 */
export const useUIStore = create<UIStore>()(
    persist(
        (set) => ({
            config: null,
            theme: 'light',
            sidebarCollapsed: false,

            setConfig: (config) => {
                set({ config });
                // Update document title
                if (config.pageTitle) {
                    document.title = config.pageTitle;
                }
            },

            setTheme: (theme) => set({ theme }),

            toggleSidebar: () =>
                set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

            setSidebarCollapsed: (collapsed) =>
                set({ sidebarCollapsed: collapsed }),
        }),
        {
            name: 'ui-storage',
            partialize: (state) => ({
                theme: state.theme,
                sidebarCollapsed: state.sidebarCollapsed,
            }),
        }
    )
);
