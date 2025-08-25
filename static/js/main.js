// static/js/main.js
// This is the complete and final version with the bug fix.

import { SocketManager } from './socket_manager.js';
import { UIManager } from './ui_manager.js';
import { SWVModule } from './swv_module.js';
// The HTModule import is kept for completeness of your original file structure.
import { HTModule } from './ht_module.js';

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Socket Manager
    const socketManager = new SocketManager();

    // Initialize UI Manager
    const uiManager = new UIManager();

    // Initialize SWV Module, passing dependencies
    const swvModule = new SWVModule(socketManager, uiManager);
    
    // Initialize HT Module
    const htModule = new HTModule(uiManager);

    // Set up initial screen
    uiManager.showScreen('welcomeScreen');

    // Register module's event handlers with socketManager.
    // NOTE: These are now handled inside swv_module.js for better organization.
    // This keeps main.js clean and focused on initialization.

    // [FIX] REMOVED the call to the non-existent checkBackendStatus function.
    // The WebSocket connection status is now the single source of truth for connectivity.
    // socketManager.checkBackendStatus(); 

    // Apply input/select styling (can be moved to a separate general_ui_utils.js if desired)
    const inputFields = document.querySelectorAll('input[type="text"], input[type="number"]');
    inputFields.forEach(input => {
        if (input.value === '') {
            input.classList.add('input-highlight');
        } else {
            input.classList.add('input-highlight', 'filled');
        }

        input.addEventListener('input', () => {
            if (input.value !== '') {
                input.classList.add('filled');
            } else {
                input.classList.remove('filled');
            }
        });
    });

    const selectFields = document.querySelectorAll('select');
    selectFields.forEach(select => {
        select.classList.add('select-highlight');
    });
});
