import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useAuthStore } from '@/stores/authStore';
import { useUIStore } from '@/stores/uiStore';
import { apiClient } from '@/services/api-client';
import LoginPage from '@/components/Auth/LoginPage';
import ChatLayout from '@/components/Layout/ChatLayout';

/**
 * Root application component
 * Handles routing, authentication, and config loading
 */
function App() {
    const { isAuthenticated } = useAuthStore();
    const { setConfig } = useUIStore();

    // Load UI config on mount
    useEffect(() => {
        async function loadConfig() {
            try {
                const config = await apiClient.getConfig();
                setConfig(config);
            } catch (error) {
                console.error('Failed to load UI config:', error);
            }
        }
        loadConfig();
    }, [setConfig]);

    return (
        <>
            <Routes>
                <Route
                    path="/login"
                    element={
                        isAuthenticated ? <Navigate to="/chat" replace /> : <LoginPage />
                    }
                />
                <Route
                    path="/chat"
                    element={
                        isAuthenticated ? <ChatLayout /> : <Navigate to="/login" replace />
                    }
                />
                <Route path="/" element={<Navigate to="/chat" replace />} />
            </Routes>

            {/* Global toast notifications */}
            <Toaster
                position="top-right"
                toastOptions={{
                    duration: 4000,
                    style: {
                        background: '#363636',
                        color: '#fff',
                    },
                    success: {
                        duration: 3000,
                        iconTheme: {
                            primary: '#15a8a8',
                            secondary: '#fff',
                        },
                    },
                    error: {
                        duration: 5000,
                        iconTheme: {
                            primary: '#fe5d26',
                            secondary: '#fff',
                        },
                    },
                }}
            />
        </>
    );
}

export default App;
