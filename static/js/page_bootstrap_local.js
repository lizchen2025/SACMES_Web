import { bindIfPresent, getAll, getById } from './dom_utils.js';

const CLEAN_CITATION = 'Curtis, S. D.; Ploense, K. L.; Kurnik, M.; Ortega, G.; Parolo, C.; Kippin, T. E.; Plaxco, K. W.; Arroyo-Curras, N. Open source software for the Real-Time control, processing, and visualization of High-Volume Electrochemical data. Analytical Chemistry 2019, 91 (19), 12321-12328. https://doi.org/10.1021/acs.analchem.9b02553.';

async function browseFolder(inputId) {
    try {
        const res = await fetch('/browse_folder');
        const data = await res.json();
        const input = getById(inputId);

        if (data.path && input) {
            input.value = data.path;
            return;
        }

        if (data.error) {
            alert(`Folder picker unavailable: ${data.error}`);
        }
    } catch (error) {
        alert('Could not open folder picker. Please type the path manually.');
    }
}

function enableAnalysisControls() {
    ['swvBtn', 'cvBtn'].forEach((id) => {
        const button = getById(id);
        if (!button) return;

        button.disabled = false;
        button.classList.remove('opacity-50', 'cursor-not-allowed');
    });
}

async function copyCitation() {
    const citationTextarea = getById('citationText');
    const copyButton = getById('copyCitationBtn');
    if (!citationTextarea || !copyButton) return;

    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(citationTextarea.value);
        } else {
            citationTextarea.select();
            document.execCommand('copy');
        }
    } catch (error) {
        citationTextarea.select();
        document.execCommand('copy');
    }

    const originalText = copyButton.textContent;
    copyButton.textContent = 'Copied!';
    window.setTimeout(() => {
        copyButton.textContent = originalText;
    }, 2000);
}

function initPageBootstrap() {
    enableAnalysisControls();

    const citationTextarea = getById('citationText');
    if (citationTextarea) {
        citationTextarea.value = CLEAN_CITATION;
    }

    getAll('[data-browse-target]').forEach((button) => {
        bindIfPresent(button, 'click', () => browseFolder(button.dataset.browseTarget));
    });

    bindIfPresent(getById('copyCitationBtn'), 'click', copyCitation);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPageBootstrap);
} else {
    initPageBootstrap();
}
