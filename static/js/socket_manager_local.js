// static/js/socket_manager_local.js
// Simplified Socket Manager for Local Application (no user_id, no agent)

export class SocketManager {
    constructor() {
        this.socket = io({
            reconnection: true,
            reconnectionAttempts: 5,  // Limited attempts for local use
            reconnectionDelay: 1000,
            reconnectionDelayMax: 3000,
            timeout: 20000,
            upgrade: true,
            transports: ['polling', 'websocket'],
            maxHttpBufferSize: 10000000  // 10MB for large files
        });
        this.eventHandlers = {};

        this._setupSocketListeners();
        this._updateConnectionStatus('disconnected');
    }

    _setupSocketListeners() {
        this.socket.on('connect', () => {
            console.log('Connected to local SACMES server');
            this._updateConnectionStatus('connected');

            // Emit 'connect' to custom handlers
            if (this.eventHandlers['connect']) {
                this.eventHandlers['connect'].forEach(handler => handler());
            }
        });

        this.socket.on('disconnect', (reason) => {
            console.log('Disconnected from server:', reason);
            this._updateConnectionStatus('disconnected');
        });

        this.socket.on('reconnect_attempt', (attemptNumber) => {
            console.log(`Reconnecting (attempt ${attemptNumber})...`);
            this._updateConnectionStatus('reconnecting');
        });

        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`Reconnected after ${attemptNumber} attempts`);
            this._updateConnectionStatus('connected');
        });

        this.socket.on('reconnect_error', (error) => {
            console.error('Reconnection error:', error);
        });

        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this._updateConnectionStatus('disconnected');
        });

        // Forward all incoming socket events to registered handlers
        this.socket.onAny((eventName, ...args) => {
            if (this.eventHandlers[eventName]) {
                this.eventHandlers[eventName].forEach(handler => handler(...args));
            }
        });
    }

    _updateConnectionStatus(status) {
        const connectionStatusEl = document.getElementById('connectionStatus');
        if (connectionStatusEl) {
            connectionStatusEl.className = status;
            if (status === 'connected') {
                connectionStatusEl.textContent = 'Local Mode - Connected';
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

    // Public method to manually disconnect
    disconnect() {
        if (this.socket && this.socket.connected) {
            console.log('Manually disconnecting socket');
            this.socket.disconnect();
        }
    }
}
