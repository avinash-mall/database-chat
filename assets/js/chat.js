// Chat initialization and customization
// This file contains any additional chat-specific JavaScript
// The main chat functionality is provided by the vanna-chat web component

document.addEventListener('DOMContentLoaded', () => {
    // Initialize chat component when the page loads
    const chatComponent = document.querySelector('vanna-chat');

    if (chatComponent) {
        // Optional: Add any custom event listeners or configuration here
        // Example: Listen for chat events
        chatComponent.addEventListener('message-sent', (event) => {
            console.log('Message sent:', event.detail);
        });

        chatComponent.addEventListener('response-received', (event) => {
            console.log('Response received:', event.detail);
        });
    }
});
