// Artifact event listener - opens artifacts in new window
document.addEventListener('DOMContentLoaded', () => {
    const vannaChat = document.querySelector('vanna-chat');
    if (vannaChat) {
        vannaChat.addEventListener('artifact-opened', (event) => {
            const { title } = event.detail;
            const newWindow = window.open('', '_blank', 'width=900,height=700');
            if (newWindow) {
                newWindow.document.write(event.detail.getStandaloneHTML());
                newWindow.document.close();
                newWindow.document.title = title || 'Artifacts';
            }
            event.detail.preventDefault();
        });
        
        // Replace welcome message after component loads
        const replaceWelcomeMessage = () => {
            const shadowRoot = vannaChat.shadowRoot;
            if (!shadowRoot) {
                setTimeout(replaceWelcomeMessage, 100);
                return;
            }
            
            // Find and replace "Welcome to Vanna AI" with "Welcome to Agentic AI"
            const walker = document.createTreeWalker(
                shadowRoot,
                NodeFilter.SHOW_TEXT,
                null
            );
            
            let node;
            while (node = walker.nextNode()) {
                if (node.textContent.includes('Welcome to Vanna AI')) {
                    node.textContent = node.textContent.replace(/Welcome to Vanna AI/g, 'Welcome to Agentic AI');
                }
            }
            
            // Also check innerHTML for any HTML-wrapped versions
            const allElements = shadowRoot.querySelectorAll('*');
            allElements.forEach(el => {
                if (el.innerHTML && el.innerHTML.includes('Welcome to Vanna AI')) {
                    el.innerHTML = el.innerHTML.replace(/Welcome to Vanna AI/g, 'Welcome to Agentic AI');
                }
            });
        };
        
        // Try immediately and after delays to catch component initialization
        setTimeout(replaceWelcomeMessage, 500);
        setTimeout(replaceWelcomeMessage, 1000);
        setTimeout(replaceWelcomeMessage, 2000);
    }
});
