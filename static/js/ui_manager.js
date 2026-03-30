// static/js/ui_manager.js

export class UIManager {
    constructor() {
        this.welcomeScreen = document.getElementById('welcomeScreen');
        this.swvAnalysisScreen = document.getElementById('swvAnalysisScreen');
        this.visualizationArea = document.getElementById('visualizationArea');
        this.cvAnalysisScreen = document.getElementById('cvAnalysisScreen');
        this.cvVisualizationScreen = document.getElementById('cvVisualizationScreen');
        this.cvResultsScreen = document.getElementById('cvResultsScreen');
    }

    showScreen(screenId) {
        this.welcomeScreen.classList.add('hidden');
        this.swvAnalysisScreen.classList.add('hidden');
        this.visualizationArea.classList.add('hidden');
        this.cvAnalysisScreen.classList.add('hidden');
        this.cvVisualizationScreen.classList.add('hidden');
        this.cvResultsScreen.classList.add('hidden');

        const screenToShow = document.getElementById(screenId);
        if (screenToShow) {
            screenToShow.classList.remove('hidden');
        } else {
            console.warn(`Screen with ID ${screenId} not found.`);
        }
    }
}
