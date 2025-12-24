// Cookie helpers
const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    return parts.length === 2 ? parts.pop().split(';').shift() : null;
};

const setCookie = (name, value) => {
    const expires = new Date(Date.now() + 365 * 864e5).toUTCString();
    document.cookie = `${name}=${value}; expires=${expires}; path=/; SameSite=Lax`;
};

const deleteCookie = (name) => {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
};

// LDAP Login
document.addEventListener('DOMContentLoaded', () => {
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

    if (!loginForm || !loginButton || !loginButtonText || !loginError || !errorMessage) {
        return;
    }

    // Check if already logged in
    const savedUser = getCookie('vanna_user');
    if (savedUser) {
        loginContainer.classList.add('hidden');
        loggedInStatus.classList.remove('hidden');
        chatSections.classList.remove('hidden');
        loggedInUser.textContent = savedUser;
    }

    // Login form submission
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('usernameInput').value.trim();
        const password = document.getElementById('passwordInput').value;
        
        if (!username || !password) {
            loginError.classList.remove('hidden');
            errorMessage.textContent = '{{LOGIN_ERROR_MISSING_FIELDS}}';
            return;
        }

        loginButton.disabled = true;
        loginButtonText.innerHTML = '<span class="loading-spinner"></span>{{AUTHENTICATING_TEXT}}';
        loginError.classList.add('hidden');

        try {
            const credentials = btoa(`${username}:${password}`);
            const response = await fetch('/api/vanna/v2/auth_test', {
                method: 'POST',
                headers: {
                    'Authorization': `Basic ${credentials}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ test: true })
            });

            if (response.ok) {
                const data = await response.json();
                setCookie('vanna_user', username);
                setCookie('vanna_groups', data.groups ? data.groups.join(',') : 'user');
                setCookie('vanna_auth', credentials);
                
                loginContainer.classList.add('hidden');
                loggedInStatus.classList.remove('hidden');
                chatSections.classList.remove('hidden');
                loggedInUser.textContent = username;
            } else {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || '{{LOGIN_ERROR_INVALID_CREDENTIALS}}');
            }
        } catch (error) {
            loginError.classList.remove('hidden');
            errorMessage.textContent = error.message || '{{LOGIN_ERROR_INVALID_CREDENTIALS}}';
        } finally {
            loginButton.disabled = false;
            loginButtonText.textContent = '{{LOGIN_BUTTON}}';
        }
    });

    // Logout
    if (logoutButton) {
        logoutButton.addEventListener('click', () => {
            deleteCookie('vanna_user');
            deleteCookie('vanna_groups');
            deleteCookie('vanna_auth');
            loginContainer.classList.remove('hidden');
            loggedInStatus.classList.add('hidden');
            chatSections.classList.add('hidden');
            document.getElementById('usernameInput').value = '';
            document.getElementById('passwordInput').value = '';
        });
    }
});

// Intercept fetch to add auth header automatically
const originalFetch = window.fetch;
window.fetch = function(...args) {
    const authToken = getCookie('vanna_auth');
    if (authToken) {
        if (args[1]) {
            args[1].headers = args[1].headers || {};
            if (!args[1].headers['Authorization']) {
                args[1].headers['Authorization'] = `Basic ${authToken}`;
            }
        } else {
            args[1] = { headers: { 'Authorization': `Basic ${authToken}` } };
        }
    }
    return originalFetch.apply(this, args);
};

// Intercept EventSource for SSE authentication
const originalEventSource = window.EventSource;
window.EventSource = function(url, eventSourceInitDict) {
    const authToken = getCookie('vanna_auth');
    if (authToken) {
        eventSourceInitDict = eventSourceInitDict || {};
        eventSourceInitDict.headers = eventSourceInitDict.headers || {};
        if (!eventSourceInitDict.headers['Authorization']) {
            eventSourceInitDict.headers['Authorization'] = `Basic ${authToken}`;
        }
    }
    return new originalEventSource(url, eventSourceInitDict);
};
