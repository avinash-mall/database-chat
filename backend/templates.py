"""
Custom HTML templates for LDAP authentication.

This module provides a customized login page that supports username/password
authentication for LDAP, replacing the default demo dropdown.
"""


def get_ldap_login_html(
    dev_mode: bool = False,
    static_path: str = "/static",
    cdn_url: str = "https://img.vanna.ai/vanna-components.js",
    api_base_url: str = "",
) -> str:
    """Generate index HTML with LDAP username/password login.

    Args:
        dev_mode: If True, load components from local static files
        static_path: Path to static assets in dev mode
        cdn_url: CDN URL for production components
        api_base_url: Base URL for API endpoints

    Returns:
        Complete HTML page as string with LDAP login form
    """
    if dev_mode:
        component_script = f'<script type="module" src="{static_path}/vanna-components.js"></script>'
    else:
        component_script = f'<script type="module" src="{cdn_url}"></script>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vanna Agents Chat</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto+Slab:wght@400;500;600;700&family=Space+Grotesk:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        'vanna-navy': '#023d60',
                        'vanna-cream': '#e7e1cf',
                        'vanna-teal': '#15a8a8',
                        'vanna-orange': '#fe5d26',
                        'vanna-magenta': '#bf1363',
                    }},
                    fontFamily: {{
                        'sans': ['Space Grotesk', 'ui-sans-serif', 'system-ui'],
                        'serif': ['Roboto Slab', 'ui-serif', 'Georgia'],
                        'mono': ['Space Mono', 'ui-monospace', 'monospace'],
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{
            background: linear-gradient(to bottom, #e7e1cf, #ffffff, #e7e1cf);
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }}

        body::before {{
            content: '';
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 0;
            background:
                radial-gradient(circle at top left, rgba(21, 168, 168, 0.12), transparent 60%),
                radial-gradient(circle at bottom right, rgba(254, 93, 38, 0.08), transparent 65%);
        }}

        body::after {{
            content: '';
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 0;
            background-image: radial-gradient(circle at 2px 2px, rgba(2, 61, 96, 0.3) 1px, transparent 0);
            background-size: 32px 32px;
            background-image:
                radial-gradient(circle at 2px 2px, rgba(2, 61, 96, 0.3) 1px, transparent 0),
                linear-gradient(rgba(2, 61, 96, 0.1) 1px, transparent 1px),
                linear-gradient(90deg, rgba(2, 61, 96, 0.1) 1px, transparent 1px);
            background-size: 32px 32px, 100px 100px, 100px 100px;
        }}

        body > * {{
            position: relative;
            z-index: 1;
        }}

        vanna-chat {{
            width: 100%;
            height: 100%;
            display: block;
        }}

        .loading-spinner {{
            border: 3px solid #e7e1cf;
            border-top: 3px solid #15a8a8;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-right: 8px;
        }}

        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
    {component_script}
</head>
<body>
    <div class="max-w-6xl mx-auto p-5">
        <!-- Header -->
        <div class="text-center mb-8">
            <h1 class="text-4xl font-bold text-vanna-navy mb-2 font-serif">Vanna Agents</h1>
            <p class="text-lg font-mono font-bold text-vanna-teal mb-4">DATA-FIRST AGENTS</p>
            <p class="text-slate-600 mb-4">Interactive AI Assistant powered by Vanna Agents Framework</p>
        </div>

        {('    <div class="bg-vanna-orange/10 border border-vanna-orange/30 rounded-lg p-3 mb-5 text-vanna-orange text-sm font-medium">📦 Development Mode: Loading components from local assets</div>' if dev_mode else "")}

        <!-- LDAP Login Form -->
        <div id="loginContainer" class="max-w-md mx-auto mb-10 bg-white p-8 rounded-xl shadow-lg border border-vanna-teal/30">
            <div class="text-center mb-6">
                <h2 class="text-2xl font-semibold text-vanna-navy mb-2 font-serif">Login to Continue</h2>
                <p class="text-sm text-slate-600">Enter your credentials to access the chat</p>
            </div>

            <div id="loginError" class="hidden mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                <strong>Login Failed:</strong> <span id="errorMessage"></span>
            </div>

            <form id="loginForm">
                <div class="mb-4">
                    <label for="usernameInput" class="block mb-2 text-sm font-medium text-vanna-navy">Username</label>
                    <input
                        type="text"
                        id="usernameInput"
                        placeholder="Enter your username"
                        autocomplete="username"
                        class="w-full px-4 py-3 text-sm border border-vanna-teal/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-vanna-teal focus:border-transparent bg-white"
                        required
                    />
                </div>

                <div class="mb-5">
                    <label for="passwordInput" class="block mb-2 text-sm font-medium text-vanna-navy">Password</label>
                    <input
                        type="password"
                        id="passwordInput"
                        placeholder="Enter your password"
                        autocomplete="current-password"
                        class="w-full px-4 py-3 text-sm border border-vanna-teal/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-vanna-teal focus:border-transparent bg-white"
                        required
                    />
                </div>

                <button type="submit" id="loginButton" class="w-full px-4 py-3 bg-vanna-teal text-white text-sm font-medium rounded-lg hover:bg-vanna-navy focus:outline-none focus:ring-2 focus:ring-vanna-teal focus:ring-offset-2 transition disabled:bg-gray-400 disabled:cursor-not-allowed">
                    <span id="loginButtonText">Login</span>
                </button>
            </form>

            <div class="mt-5 p-3 bg-vanna-teal/10 border-l-4 border-vanna-teal rounded text-xs text-vanna-navy leading-relaxed">
                <strong>LDAP Authentication:</strong> Use your organizational credentials to log in.
            </div>
        </div>

        <!-- Logged In Status (hidden by default) -->
        <div id="loggedInStatus" class="hidden text-center p-4 bg-vanna-teal/10 border border-vanna-teal/30 rounded-lg mb-5">
            Logged in as <span id="loggedInUser" class="font-semibold text-vanna-navy"></span>
            <br>
            <button id="logoutButton" class="mt-2 px-3 py-1.5 bg-vanna-navy text-white text-xs rounded hover:bg-vanna-teal transition">
                Logout
            </button>
        </div>

        <!-- Chat Container (hidden by default) -->
        <div id="chatSections" class="hidden">
            <div class="bg-white rounded-xl shadow-lg h-[600px] overflow-hidden border border-vanna-teal/30">
                <vanna-chat
                    api-base="{api_base_url}"
                    sse-endpoint="{api_base_url}/api/vanna/v2/chat_sse"
                    ws-endpoint="{api_base_url}/api/vanna/v2/chat_websocket"
                    poll-endpoint="{api_base_url}/api/vanna/v2/chat_poll">
                </vanna-chat>
            </div>

            <div class="mt-8 p-5 bg-white rounded-lg shadow border border-vanna-teal/30">
                <h3 class="text-lg font-semibold text-vanna-navy mb-3 font-serif">API Endpoints</h3>
                <ul class="space-y-2">
                    <li class="p-2 bg-vanna-cream/50 rounded font-mono text-sm">
                        <span class="font-bold text-vanna-teal mr-2">POST</span>{api_base_url}/api/vanna/v2/chat_sse - Server-Sent Events streaming
                    </li>
                    <li class="p-2 bg-vanna-cream/50 rounded font-mono text-sm">
                        <span class="font-bold text-vanna-teal mr-2">WS</span>{api_base_url}/api/vanna/v2/chat_websocket - WebSocket real-time chat
                    </li>
                    <li class="p-2 bg-vanna-cream/50 rounded font-mono text-sm">
                        <span class="font-bold text-vanna-teal mr-2">POST</span>{api_base_url}/api/vanna/v2/chat_poll - Request/response polling
                    </li>
                    <li class="p-2 bg-vanna-cream/50 rounded font-mono text-sm">
                        <span class="font-bold text-vanna-teal mr-2">GET</span>{api_base_url}/health - Health check
                    </li>
                </ul>
            </div>
        </div>
    </div>

    <script>
        // Cookie helpers
        const getCookie = (name) => {{
            const value = `; ${{document.cookie}}`;
            const parts = value.split(`; ${{name}}=`);
            return parts.length === 2 ? parts.pop().split(';').shift() : null;
        }};

        const setCookie = (name, value) => {{
            const expires = new Date(Date.now() + 365 * 864e5).toUTCString();
            document.cookie = `${{name}}=${{value}}; expires=${{expires}}; path=/; SameSite=Lax`;
        }};

        const deleteCookie = (name) => {{
            document.cookie = `${{name}}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
        }};

        // LDAP Login
        document.addEventListener('DOMContentLoaded', () => {{
            const loginForm = document.getElementById('loginForm');
            const loginButton = document.getElementById('loginButton');
            const loginButtonText = document.getElementById('loginButtonText');
            const loginError = document.getElementById('loginError');
            const errorMessage = document.getElementById('errorMessage');
            const loginContainer = document.getElementById('loginContainer');
            const loggedInStatus = document.getElementById('loggedInStatus');
            const chatSections = document.getElementById('chatSections');
            const loggedInUser = document.getElementById('loggedInUser');
            const logoutButton = document.getElementById('logoutButton');

            // Check if already logged in via cookies
            const savedUser = getCookie('vanna_user');
            if (savedUser) {{
                loginContainer.classList.add('hidden');
                loggedInStatus.classList.remove('hidden');
                chatSections.classList.remove('hidden');
                loggedInUser.textContent = savedUser;
            }}

            // Login form submission
            loginForm.addEventListener('submit', async (e) => {{
                e.preventDefault();
                
                const username = document.getElementById('usernameInput').value.trim();
                const password = document.getElementById('passwordInput').value;
                
                if (!username || !password) {{
                    loginError.classList.remove('hidden');
                    errorMessage.textContent = 'Please enter both username and password.';
                    return;
                }}

                // Show loading state
                loginButton.disabled = true;
                loginButtonText.innerHTML = '<span class="loading-spinner"></span>Authenticating...';
                loginError.classList.add('hidden');

                try {{
                    // Create Basic Auth header and test against backend
                    const credentials = btoa(`${{username}}:${{password}}`);
                    
                    // Test authentication by making a request to health endpoint with auth
                    const response = await fetch('/api/vanna/v2/auth_test', {{
                        method: 'POST',
                        headers: {{
                            'Authorization': `Basic ${{credentials}}`,
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{ test: true }})
                    }});

                    if (response.ok) {{
                        const data = await response.json();
                        
                        // Store credentials in cookies for subsequent requests
                        setCookie('vanna_user', username);
                        setCookie('vanna_groups', data.groups ? data.groups.join(',') : 'user');
                        setCookie('vanna_auth', credentials);
                        
                        // Update UI
                        loginContainer.classList.add('hidden');
                        loggedInStatus.classList.remove('hidden');
                        chatSections.classList.remove('hidden');
                        loggedInUser.textContent = username;
                    }} else {{
                        const errorData = await response.json().catch(() => ({{}}));
                        throw new Error(errorData.error || 'Invalid credentials');
                    }}
                }} catch (error) {{
                    loginError.classList.remove('hidden');
                    errorMessage.textContent = error.message || 'Authentication failed. Please check your credentials.';
                }} finally {{
                    loginButton.disabled = false;
                    loginButtonText.textContent = 'Login';
                }}
            }});

            // Logout button
            logoutButton.addEventListener('click', () => {{
                deleteCookie('vanna_user');
                deleteCookie('vanna_groups');
                deleteCookie('vanna_auth');
                loginContainer.classList.remove('hidden');
                loggedInStatus.classList.add('hidden');
                chatSections.classList.add('hidden');
                document.getElementById('usernameInput').value = '';
                document.getElementById('passwordInput').value = '';
            }});
        }});

        // Intercept fetch to add auth header automatically
        const originalFetch = window.fetch;
        window.fetch = function(...args) {{
            const authToken = getCookie('vanna_auth');
            if (authToken && args[1]) {{
                args[1].headers = args[1].headers || {{}};
                if (!args[1].headers['Authorization']) {{
                    args[1].headers['Authorization'] = `Basic ${{authToken}}`;
                }}
            }} else if (authToken && !args[1]) {{
                args[1] = {{
                    headers: {{
                        'Authorization': `Basic ${{authToken}}`
                    }}
                }};
            }}
            return originalFetch.apply(this, args);
        }};

        // Cookie helper for fetch interceptor
        function getCookie(name) {{
            const value = `; ${{document.cookie}}`;
            const parts = value.split(`; ${{name}}=`);
            return parts.length === 2 ? parts.pop().split(';').shift() : null;
        }}
    </script>

    <script>
        // Artifact demo event listener
        document.addEventListener('DOMContentLoaded', () => {{
            const vannaChat = document.querySelector('vanna-chat');

            if (vannaChat) {{
                vannaChat.addEventListener('artifact-opened', (event) => {{
                    const {{ artifactId, type, title, trigger }} = event.detail;
                    console.log('🎨 Artifact Event:', {{ artifactId, type, title, trigger }});

                    setTimeout(() => {{
                        const newWindow = window.open('', '_blank', 'width=900,height=700');
                        if (newWindow) {{
                            newWindow.document.write(event.detail.getStandaloneHTML());
                            newWindow.document.close();
                            newWindow.document.title = title || 'Vanna Artifact';
                            console.log(`📱 Opened ${{title}} in new window`);
                        }}
                    }}, 100);

                    event.detail.preventDefault();
                    console.log('✋ Showing placeholder in chat instead of full artifact');
                }});

                console.log('🎯 Artifact demo mode: All artifacts will open externally');
            }}
        }});

        // Fallback if web component doesn't load
        if (!customElements.get('vanna-chat')) {{
            setTimeout(() => {{
                if (!customElements.get('vanna-chat')) {{
                    document.querySelector('vanna-chat').innerHTML = `
                        <div class="p-10 text-center text-gray-600">
                            <h3 class="text-xl font-semibold mb-2">Vanna Chat Component</h3>
                            <p class="mb-2">Web component failed to load. Please check your connection.</p>
                            <p class="text-sm text-gray-400">
                                {("Loading from: local static assets" if dev_mode else f"Loading from: {cdn_url}")}
                            </p>
                        </div>
                    `;
                }}
            }}, 2000);
        }}
    </script>
</body>
</html>"""
