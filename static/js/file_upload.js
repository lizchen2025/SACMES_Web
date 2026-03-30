// static/js/file_upload.js
// File Upload Component for Local Application

export class FileUploader {
    constructor(socketManager, prefix = '') {
        this.socketManager = socketManager;
        this.prefix = prefix;
        this.uploadedFiles = []; // Track uploaded files
        this.setupUI();
    }

    setupUI() {
        const dropZoneId = this.prefix ? `${this.prefix}DropZone` : 'dropZone';
        const fileInputId = this.prefix ? `${this.prefix}FileInput` : 'fileInput';

        const dropZone = document.getElementById(dropZoneId);
        const fileInput = document.getElementById(fileInputId);

        if (!dropZone || !fileInput) {
            console.warn(`File upload UI elements not found for prefix: ${this.prefix || 'default'}`);
            return;
        }

        // Click to upload
        dropZone.addEventListener('click', () => fileInput.click());

        // File selection via dialog
        fileInput.addEventListener('change', (e) => {
            this.handleFiles(Array.from(e.target.files));
            fileInput.value = ''; // Reset input
        });

        // Drag and drop functionality
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('border-blue-500', 'bg-blue-50');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('border-blue-500', 'bg-blue-50');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('border-blue-500', 'bg-blue-50');

            const files = Array.from(e.dataTransfer.files);
            this.handleFiles(files);
        });
    }

    async handleFiles(files) {
        console.log(`Processing ${files.length} file(s)...`);

        for (const file of files) {
            // Check file extension
            const allowedExtensions = ['.txt', '.dta', '.csv'];
            const fileExt = '.' + file.name.split('.').pop().toLowerCase();

            if (!allowedExtensions.includes(fileExt)) {
                alert(`File "${file.name}" has invalid extension. Only .txt, .dta, .csv allowed.`);
                continue;
            }

            // Check file size (5MB limit)
            const MAX_SIZE = 5 * 1024 * 1024;
            if (file.size > MAX_SIZE) {
                alert(`File "${file.name}" is too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Maximum is 5MB.`);
                continue;
            }

            await this.uploadFile(file);
        }
    }

    async uploadFile(file) {
        try {
            // Read file content
            const content = await this.readFileContent(file);

            // Send via SocketIO (reuse existing stream_instrument_data event)
            this.socketManager.emit('stream_instrument_data', {
                filename: file.name,
                content: content
            });

            console.log(`Uploaded: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`);

            // Show user feedback
            this.showUploadFeedback(file.name, true);

        } catch (error) {
            console.error(`Error uploading ${file.name}:`, error);
            this.showUploadFeedback(file.name, false, error.message);
        }
    }

    readFileContent(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = () => reject(new Error('Failed to read file'));
            reader.readAsText(file);
        });
    }

    showUploadFeedback(filename, success, errorMsg = '') {
        const statusId = this.prefix ? `${this.prefix}UploadStatus` : 'uploadStatus';
        const statusElement = document.getElementById(statusId);
        if (!statusElement) return;

        if (success) {
            statusElement.textContent = `[OK] Uploaded: ${filename}`;
            statusElement.className = 'text-sm text-green-600 mt-2';

            // Add to uploaded files list
            this.uploadedFiles.push({
                name: filename,
                timestamp: new Date().toLocaleTimeString()
            });
            this.updateUploadedFilesList();
        } else {
            statusElement.textContent = `[X] Failed: ${filename} - ${errorMsg}`;
            statusElement.className = 'text-sm text-red-600 mt-2';
        }

        // Clear after 3 seconds
        setTimeout(() => {
            statusElement.textContent = '';
        }, 3000);
    }

    updateUploadedFilesList() {
        const listId = this.prefix ? `${this.prefix}UploadedFilesList` : 'uploadedFilesList';
        const containerId = this.prefix ? `${this.prefix}UploadedFilesContainer` : 'uploadedFilesContainer';

        const listElement = document.getElementById(listId);
        const containerElement = document.getElementById(containerId);

        if (!listElement || !containerElement) return;

        if (this.uploadedFiles.length === 0) {
            listElement.classList.add('hidden');
            return;
        }

        listElement.classList.remove('hidden');

        // Build file list HTML
        const filesHTML = this.uploadedFiles.map((file, index) => `
            <div class="flex justify-between items-center py-1 px-2 hover:bg-gray-50 text-xs">
                <span class="text-gray-700">${index + 1}. ${file.name}</span>
                <span class="text-gray-500">${file.timestamp}</span>
            </div>
        `).join('');

        containerElement.innerHTML = filesHTML;
    }
}
