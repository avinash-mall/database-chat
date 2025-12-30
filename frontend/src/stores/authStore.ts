import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AuthState, User } from '@/types';

interface AuthStore extends AuthState {
    setAuth: (auth: Partial<AuthState>) => void;
    setUser: (user: User) => void;
    clearAuth: () => void;
}

/**
 * Zustand store for authentication state
 * Persisted to localStorage for session management
 */
export const useAuthStore = create<AuthStore>()(
    persist(
        (set) => ({
            user: null,
            isAuthenticated: false,
            token: null,

            setAuth: (auth) => set((state) => ({ ...state, ...auth })),

            setUser: (user) => set({ user, isAuthenticated: true }),

            clearAuth: () =>
                set({
                    user: null,
                    isAuthenticated: false,
                    token: null,
                }),
        }),
        {
            name: 'auth-storage',
            partialize: (state) => ({
                user: state.user,
                isAuthenticated: state.isAuthenticated,
                token: state.token,
            }),
        }
    )
);
