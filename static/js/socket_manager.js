// static/js/socket_manager.js

export class SocketManager {
    constructor() {
        this.socket = io({
            reconnection: true,
            reconnectionAttempts: Infinity,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 60000,  // Extended timeout to match backend (60s)

            // Additional settings for OpenShift stability
            forceNew: false,
            upgrade: true,
            rememberUpgrade: true,
            transports: ['websocket', 'polling']
        });
        this.eventHandlers = {}; // To store custom event handlers

        this._setupSocketListeners();
        this._updateConnectionStatus('disconnected'); // Initial status
    }

    _setupSocketListeners() {
        this.socket.on('connect', () => {
            console.log('Socket.IO connected!');
            this._updateConnectionStatus('connected');
            // Emit 'connect' to our custom handlers, so other modules know we are connected.
            if (this.eventHandlers['connect']) {
                this.eventHandlers['connect'].forEach(handler => handler());
            }
        });

        this.socket.on('disconnect', (reason) => {
            console.log('Socket.IO disconnected:', reason);
            this._updateConnectionStatus('disconnected');
        });

        this.socket.on('reconnect_attempt', (attemptNumber) => {
            console.log(`Socket.IO reconnecting (attempt ${attemptNumber})...`);
            this._updateConnectionStatus('reconnecting');
        });

        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`Socket.IO reconnected after ${attemptNumber} attempts.`);
            this._updateConnectionStatus('connected');
        });

        this.socket.on('reconnect_error', (error) => {
            console.error('Socket.IO reconnection error:', error);
            this._updateConnectionStatus('disconnected');
        });

        this.socket.on('connect_error', (error) => {
            console.error('Socket.IO connection error:', error);
            this._updateConnectionStatus('disconnected');
        });

        // Forward all incoming socket events to custom registered handlers
        this.socket.onAny((eventName, ...args) => {
            if (this.eventHandlers[eventName]) {
                this.eventHandlers[eventName].forEach(handler => handler(...args));
            }
        });
    }

    _updateConnectionStatus(status) {
        const connectionStatusEl = document.getElementById('connectionStatus');
        if (connectionStatusEl) {
            connectionStatusEl.className = ''; // Clear existing classes
            connectionStatusEl.classList.add(status);
            if (status === 'connected') {
                connectionStatusEl.textContent = 'Connected';
            } else if (status === 'disconnected') {
                connectionStatusEl.textContent = 'Disconnected';
            } else if (status === 'reconnecting') {
                connectionStatusEl.textContent = 'Reconnecting...';
            }
        }
    }

    // Public method to emit events
    emit(eventName, data) {
        this.socket.emit(eventName, data);
    }

    // Public method to register handlers for specific socket events
    on(eventName, handler) {
        if (!this.eventHandlers[eventName]) {
            this.eventHandlers[eventName] = [];
        }
        this.eventHandlers[eventName].push(handler);
    }

    // [REMOVED] The checkBackendStatus function is no longer needed
    // as it was causing console errors. WebSocket status is sufficient.
}
