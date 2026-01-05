// static/js/main_local.js
// Main Entry Point for SACMES Local Application

import { SocketManager } from './socket_manager_local.js';
import { UIManager } from './ui_manager.js';
import { SWVModule } from './swv_module.js';
import { CVModule } from './cv_module.js';
import { HTModule } from './ht_module.js';
import { FolderMonitor } from './folder_monitor.js';
import { DiagnosticsPanel } from './diagnostics_panel.js';

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing SACMES Local Application...');

    // Initialize Socket Manager
    const socketManager = new SocketManager();

    // Expose socketManager globally for access across modules
    window.socketManager = socketManager;

    // Initialize UI Manager
    const uiManager = new UIManager();

    // Expose uiManager globally for navigation
    window.uiManager = uiManager;

    // Initialize Analysis Modules
    const swvModule = new SWVModule(socketManager, uiManager);
    const cvModule = new CVModule(socketManager, uiManager);
    const htModule = new HTModule(socketManager, uiManager);

    // Expose modules globally for data access
    window.swvModule = swvModule;
    window.cvModule = cvModule;
    window.htModule = htModule;

    // Initialize Folder Monitoring for each analysis type
    const swvFolderMonitor = new FolderMonitor(socketManager, 'swv');
    const cvFolderMonitor = new FolderMonitor(socketManager, 'cv');
    const htFolderMonitor = new FolderMonitor(socketManager, 'ht');

    // Initialize Diagnostics Panel
    const diagnosticsPanel = new DiagnosticsPanel(socketManager);

    // Setup main navigation buttons
    setupNavigation(uiManager);

    // Show welcome screen on startup
    uiManager.showScreen('welcomeScreen');

    // Apply input styling
    applyInputStyling();

    console.log('SACMES Local Application initialized successfully');
});

function setupNavigation(uiManager) {
    // SWV button
    const swvBtn = document.getElementById('swvBtn');
    if (swvBtn) {
        swvBtn.addEventListener('click', () => {
            uiManager.showScreen('swvAnalysisScreen');
        });
    }

    // CV button
    const cvBtn = document.getElementById('cvBtn');
    if (cvBtn) {
        cvBtn.addEventListener('click', () => {
            uiManager.showScreen('cvAnalysisScreen');
        });
    }

    // HT button
    const htBtn = document.getElementById('htBtn');
    if (htBtn) {
        htBtn.addEventListener('click', () => {
            uiManager.showScreen('htAnalysisScreen');
        });
    }

    // Back buttons - return to welcome screen
    const backButtons = document.querySelectorAll('[id^="backToWelcome"]');
    backButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            uiManager.showScreen('welcomeScreen');
        });
    });
}

function applyInputStyling() {
    // Apply input/select styling for better UX
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
}
