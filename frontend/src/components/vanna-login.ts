/**
 * Login component for LDAP authentication with Vanna
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { vannaDesignTokens } from '../styles/vanna-design-tokens.js';

@customElement('vanna-login')
export class VannaLogin extends LitElement {
    static styles = [
        vannaDesignTokens,
        css`
      :host {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100vh;
        background: linear-gradient(135deg, var(--vanna-background-default) 0%, var(--vanna-background-higher) 100%);
        font-family: var(--vanna-font-family-default);
      }

      .login-container {
        background: var(--vanna-background-default);
        border-radius: var(--vanna-border-radius-xl);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
        padding: var(--vanna-space-10);
        width: 100%;
        max-width: 400px;
        margin: var(--vanna-space-4);
      }

      .login-header {
        text-align: center;
        margin-bottom: var(--vanna-space-8);
      }

      .login-logo {
        width: 64px;
        height: 64px;
        margin: 0 auto var(--vanna-space-4);
        background: linear-gradient(135deg, var(--vanna-accent-primary-default) 0%, var(--vanna-accent-primary-stronger) 100%);
        border-radius: var(--vanna-border-radius-lg);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 24px;
        font-weight: 700;
      }

      .login-title {
        font-size: 24px;
        font-weight: 700;
        color: var(--vanna-foreground-default);
        margin: 0 0 var(--vanna-space-2);
      }

      .login-subtitle {
        font-size: 14px;
        color: var(--vanna-foreground-dimmest);
      }

      .form-group {
        margin-bottom: var(--vanna-space-5);
      }

      .form-label {
        display: block;
        font-size: 14px;
        font-weight: 500;
        color: var(--vanna-foreground-default);
        margin-bottom: var(--vanna-space-2);
      }

      .form-input {
        width: 100%;
        padding: var(--vanna-space-3) var(--vanna-space-4);
        font-size: 14px;
        border: 1px solid var(--vanna-outline-default);
        border-radius: var(--vanna-border-radius-md);
        background: var(--vanna-background-higher);
        color: var(--vanna-foreground-default);
        transition: border-color 0.2s, box-shadow 0.2s;
        box-sizing: border-box;
      }

      .form-input:focus {
        outline: none;
        border-color: var(--vanna-accent-primary-default);
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
      }

      .form-input::placeholder {
        color: var(--vanna-foreground-dimmest);
      }

      .login-button {
        width: 100%;
        padding: var(--vanna-space-4);
        font-size: 14px;
        font-weight: 600;
        color: white;
        background: linear-gradient(135deg, var(--vanna-accent-primary-default) 0%, var(--vanna-accent-primary-stronger) 100%);
        border: none;
        border-radius: var(--vanna-border-radius-md);
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
      }

      .login-button:hover:not(:disabled) {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
      }

      .login-button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }

      .error-message {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: var(--vanna-border-radius-md);
        padding: var(--vanna-space-3) var(--vanna-space-4);
        margin-bottom: var(--vanna-space-5);
        color: #ef4444;
        font-size: 14px;
      }

      .success-message {
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.3);
        border-radius: var(--vanna-border-radius-md);
        padding: var(--vanna-space-3) var(--vanna-space-4);
        margin-bottom: var(--vanna-space-5);
        color: #22c55e;
        font-size: 14px;
      }
    `
    ];

    @property() apiBase = '';
    @property() title = 'Vanna AI';
    @property() subtitle = 'Sign in to continue';

    @state() private username = '';
    @state() private password = '';
    @state() private isLoading = false;
    @state() private error = '';
    @state() private success = '';

    private handleUsernameInput(e: Event) {
        const input = e.target as HTMLInputElement;
        this.username = input.value;
        this.error = '';
    }

    private handlePasswordInput(e: Event) {
        const input = e.target as HTMLInputElement;
        this.password = input.value;
        this.error = '';
    }

    private handleKeyPress(e: KeyboardEvent) {
        if (e.key === 'Enter') {
            this.handleLogin();
        }
    }

    private async handleLogin() {
        if (!this.username.trim() || !this.password.trim()) {
            this.error = 'Please enter both username and password';
            return;
        }

        this.isLoading = true;
        this.error = '';

        try {
            // Create Basic Auth header
            const credentials = btoa(`${this.username}:${this.password}`);
            const authHeader = `Basic ${credentials}`;

            // Test authentication against the API
            const response = await fetch(`${this.apiBase}/api/vanna/v2/chat_sse`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': authHeader,
                },
                body: JSON.stringify({
                    message: '',
                    metadata: { auth_test: true }
                }),
            });

            if (response.ok || response.status === 200) {
                this.success = 'Login successful! Redirecting...';

                // Store auth in session storage
                sessionStorage.setItem('vanna_auth', authHeader);
                sessionStorage.setItem('vanna_user', this.username);

                // Dispatch login event with auth header
                this.dispatchEvent(new CustomEvent('login-success', {
                    detail: {
                        username: this.username,
                        authHeader: authHeader
                    },
                    bubbles: true,
                    composed: true
                }));

            } else if (response.status === 401) {
                this.error = 'Invalid username or password';
            } else {
                this.error = `Authentication failed: ${response.statusText}`;
            }
        } catch (err) {
            this.error = err instanceof Error ? err.message : 'Connection failed';
        } finally {
            this.isLoading = false;
        }
    }

    render() {
        return html`
      <div class="login-container">
        <div class="login-header">
          <div class="login-logo">VA</div>
          <h1 class="login-title">${this.title}</h1>
          <p class="login-subtitle">${this.subtitle}</p>
        </div>

        ${this.error ? html`<div class="error-message">${this.error}</div>` : ''}
        ${this.success ? html`<div class="success-message">${this.success}</div>` : ''}

        <div class="form-group">
          <label class="form-label" for="username">Username</label>
          <input
            type="text"
            id="username"
            class="form-input"
            placeholder="Enter your username"
            .value=${this.username}
            @input=${this.handleUsernameInput}
            @keypress=${this.handleKeyPress}
            ?disabled=${this.isLoading}
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="password">Password</label>
          <input
            type="password"
            id="password"
            class="form-input"
            placeholder="Enter your password"
            .value=${this.password}
            @input=${this.handlePasswordInput}
            @keypress=${this.handleKeyPress}
            ?disabled=${this.isLoading}
          />
        </div>

        <button
          class="login-button"
          @click=${this.handleLogin}
          ?disabled=${this.isLoading || !this.username.trim() || !this.password.trim()}
        >
          ${this.isLoading ? 'Signing in...' : 'Sign In'}
        </button>
      </div>
    `;
    }
}

declare global {
    interface HTMLElementTagNameMap {
        'vanna-login': VannaLogin;
    }
}
