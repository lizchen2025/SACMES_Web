// static/js/ui_manager.js

export class UIManager {
    constructor() {
        this.welcomeScreen = document.getElementById('welcomeScreen');
        this.swvAnalysisScreen = document.getElementById('swvAnalysisScreen');
        this.visualizationArea = document.getElementById('visualizationArea');
        // ADDED: Reference for the new HT Analysis screen
        this.htAnalysisScreen = document.getElementById('htAnalysisScreen');
        // ADDED: References for CV screens
        this.cvAnalysisScreen = document.getElementById('cvAnalysisScreen');
        this.cvVisualizationScreen = document.getElementById('cvVisualizationScreen');
    }

    showScreen(screenId) {
        this.welcomeScreen.classList.add('hidden');
        this.swvAnalysisScreen.classList.add('hidden');
        this.visualizationArea.classList.add('hidden');
        // ADDED: Hide the new screen by default
        this.htAnalysisScreen.classList.add('hidden');
        // ADDED: Hide CV screens by default
        this.cvAnalysisScreen.classList.add('hidden');
        this.cvVisualizationScreen.classList.add('hidden');

        const screenToShow = document.getElementById(screenId);
        if (screenToShow) {
            screenToShow.classList.remove('hidden');
        } else {
            console.warn(`Screen with ID ${screenId} not found.`);
        }
    }
}
