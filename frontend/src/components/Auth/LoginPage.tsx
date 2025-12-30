import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuthStore } from '@/stores/authStore';
import { apiClient } from '@/services/api-client';

/**
 * Login Page Component
 * 
 * Features:
 * - LDAP authentication
 * - Form validation
 * - Loading states
 * - Error handling
 * - Session persistence
 */
export default function LoginPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const { setAuth } = useAuthStore();
    const navigate = useNavigate();

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();

        if (!username || !password) {
            toast.error('Please enter both username and password');
            return;
        }

        setIsLoading(true);

        try {
            const response = await apiClient.login(username, password);

            // Store user in global state
            setAuth({
                user: {
                    id: response.user,
                    username: response.user,
                    email: response.email,
                    groups: response.groups,
                    isAdmin: response.is_admin,
                },
                isAuthenticated: true,
                token: btoa(`${username}:${password}`),
            });

            toast.success(`Welcome, ${response.user}!`);
            navigate('/chat');
        } catch (error) {
            toast.error((error as Error).message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-vanna-cream to-white px-4">
            <div className="w-full max-w-md">
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold text-vanna-navy mb-2 font-serif">
                        Database Chat AI
                    </h1>
                    <p className="text-gray-600">
                        Interactive AI Assistant for Database Queries
                    </p>
                </div>

                <div className="bg-white p-8 rounded-xl shadow-lg border border-vanna-teal/30">
                    <h2 className="text-2xl font-semibold text-center mb-6">
                        Login to Continue
                    </h2>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label
                                htmlFor="username"
                                className="block text-sm font-medium text-gray-700 mb-1"
                            >
                                Username
                            </label>
                            <input
                                id="username"
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-vanna-teal focus:border-transparent transition"
                                placeholder="Enter your username"
                                disabled={isLoading}
                                autoComplete="username"
                                autoFocus
                            />
                        </div>

                        <div>
                            <label
                                htmlFor="password"
                                className="block text-sm font-medium text-gray-700 mb-1"
                            >
                                Password
                            </label>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-vanna-teal focus:border-transparent transition"
                                placeholder="Enter your password"
                                disabled={isLoading}
                                autoComplete="current-password"
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full px-4 py-3 bg-vanna-teal text-white rounded-lg hover:bg-vanna-navy transition font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                        >
                            {isLoading ? (
                                <>
                                    <svg
                                        className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                    >
                                        <circle
                                            className="opacity-25"
                                            cx="12"
                                            cy="12"
                                            r="10"
                                            stroke="currentColor"
                                            strokeWidth="4"
                                        ></circle>
                                        <path
                                            className="opacity-75"
                                            fill="currentColor"
                                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                        ></path>
                                    </svg>
                                    Authenticating...
                                </>
                            ) : (
                                'Login'
                            )}
                        </button>
                    </form>

                    <p className="mt-6 text-sm text-gray-500 text-center">
                        🔒 LDAP Authentication: Use your organizational credentials
                    </p>
                </div>

                <p className="text-center text-xs text-gray-500 mt-8">
                    Powered by Vanna AI Agents Framework
                </p>
            </div>
        </div>
    );
}
