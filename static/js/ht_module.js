// static/js/ht_module.js

// FIXED: Added the 'export' keyword before the class definition.
export class HTModule {
    constructor(uiManager) {
        this.uiManager = uiManager;

        // --- State Management for Annotations ---
        this.annotations = {}; // e.g., { "A1": "Control", "B7": "Sample X" }
        this.currentEditingWell = null;

        // --- DOM Element Caching ---
        this.dom = {
            htBtn: document.getElementById('htBtn'),
            backToWelcomeBtn: document.getElementById('backToWelcomeFromHT'),
            accordions: document.querySelectorAll('.accordion-header'),
            wells: document.querySelectorAll('.well'),
            annotationModal: document.getElementById('annotationModal'),
            annotationWellPosition: document.getElementById('annotationWellPosition'),
            annotationInput: document.getElementById('annotationInput'),
            saveAnnotationBtn: document.getElementById('saveAnnotationBtn'),
            cancelAnnotationBtn: document.getElementById('cancelAnnotationBtn'),
            closeAnnotationModal: document.getElementById('closeAnnotationModal'),
            annotationTableContainer: document.getElementById('annotationTableContainer'),
            annotationTableBody: document.querySelector('#annotationTable tbody'),
        };

        this._setupEventListeners();
    }

    _setupEventListeners() {
        // Event listener to show the HT Analysis screen
        this.dom.htBtn.addEventListener('click', () => {
            this.uiManager.showScreen('htAnalysisScreen');
        });

        // Event listeners for the collapsible parameter sections
        this.dom.accordions.forEach(button => {
            button.addEventListener('click', () => {
                const content = button.nextElementSibling;
                button.classList.toggle('active');

                if (content.style.maxHeight) {
                    content.style.maxHeight = null;
                } else {
                    // Use scrollHeight to get the full height of the content for the animation
                    content.style.maxHeight = content.scrollHeight + "px";
                }
            });
        });

        // Event listeners for each well to open the annotation modal
        this.dom.wells.forEach(well => {
            well.addEventListener('click', (event) => {
                this._handleWellClick(event.target);
            });
        });

        // Event listeners for the annotation modal buttons
        this.dom.saveAnnotationBtn.addEventListener('click', this._handleSaveAnnotation.bind(this));
        this.dom.cancelAnnotationBtn.addEventListener('click', this._hideAnnotationModal.bind(this));
        this.dom.closeAnnotationModal.addEventListener('click', this._hideAnnotationModal.bind(this));
        this.dom.backToWelcomeBtn.addEventListener('click', () => this.uiManager.showScreen('welcomeScreen'));
    }

    _handleWellClick(wellElement) {
        const position = wellElement.dataset.position;
        this.currentEditingWell = position;
        this.dom.annotationWellPosition.textContent = position;
        this.dom.annotationInput.value = this.annotations[position] || '';
        this.dom.annotationModal.classList.remove('hidden');
        this.dom.annotationInput.focus();
    }

    _hideAnnotationModal() {
        this.dom.annotationModal.classList.add('hidden');
        this.currentEditingWell = null;
    }

    _handleSaveAnnotation() {
        if (!this.currentEditingWell) return;

        const annotationText = this.dom.annotationInput.value.trim();
        const position = this.currentEditingWell;

        if (annotationText) {
            this.annotations[position] = annotationText;
        } else {
            delete this.annotations[position]; // Remove annotation if text is empty
        }

        this._renderAnnotationTable();
        this._hideAnnotationModal();
    }

    _renderAnnotationTable() {
        // Clear existing table rows
        this.dom.annotationTableBody.innerHTML = '';

        // Get sorted keys to display annotations in order (e.g., A1, A2, B1, B2)
        const sortedPositions = Object.keys(this.annotations).sort((a, b) => {
            const rowA = a.charAt(0);
            const colA = parseInt(a.substring(1));
            const rowB = b.charAt(0);
            const colB = parseInt(b.substring(1));

            if (rowA < rowB) return -1;
            if (rowA > rowB) return 1;
            return colA - colB;
        });

        if (sortedPositions.length > 0) {
            this.dom.annotationTableContainer.classList.remove('hidden');
            sortedPositions.forEach(position => {
                const annotation = this.annotations[position];
                const row = this.dom.annotationTableBody.insertRow();
                row.innerHTML = `
                    <td class="px-6 py-4 font-medium text-gray-900 whitespace-nowrap">${position}</td>
                    <td class="px-6 py-4">${annotation}</td>
                `;
            });
        } else {
            this.dom.annotationTableContainer.classList.add('hidden');
        }
    }
}
