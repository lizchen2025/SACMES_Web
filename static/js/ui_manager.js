// static/js/ui_manager.js

export class UIManager {
    constructor() {
        this.welcomeScreen = document.getElementById('welcomeScreen');
        this.swvAnalysisScreen = document.getElementById('swvAnalysisScreen');
        this.visualizationArea = document.getElementById('visualizationArea');
        // ADDED: Reference for the new HT Analysis screen
        this.htAnalysisScreen = document.getElementById('htAnalysisScreen');
    }

    showScreen(screenId) {
        this.welcomeScreen.classList.add('hidden');
        this.swvAnalysisScreen.classList.add('hidden');
        this.visualizationArea.classList.add('hidden');
        // ADDED: Hide the new screen by default
        this.htAnalysisScreen.classList.add('hidden');

        const screenToShow = document.getElementById(screenId);
        if (screenToShow) {
            screenToShow.classList.remove('hidden');
        } else {
            console.warn(`Screen with ID ${screenId} not found.`);
        }
    }
}
