// static/js/socket_manager.js

export class SocketManager {
    constructor() {
        this.socket = io({
            reconnection: true,
            reconnectionAttempts: Infinity,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 120000,  // Extended timeout to match backend (120s, was 60s)

            // Additional settings for OpenShift stability
            forceNew: false,
            upgrade: true,
            rememberUpgrade: true,
            transports: ['websocket', 'polling'],

            // Increase max buffer size for large CV data files (must match backend)
            maxHttpBufferSize: 10000000  // 10MB to match backend setting
        });
        this.eventHandlers = {}; // To store custom event handlers

        this._setupSocketListeners();
        this._setupPageUnloadHandler();
        this._updateConnectionStatus('disconnected'); // Initial status
    }

    _setupSocketListeners() {
        this.socket.on('connect', () => {
            console.log('Socket.IO connected!');
            this._updateConnectionStatus('connected');

            // Auto-reconnect: Re-register web viewer if user_id exists
            this._handleReconnection();

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

    _handleReconnection() {
        // Check if user_id exists (from window.getCurrentUserId function in index.html)
        if (typeof window.getCurrentUserId === 'function') {
            const userId = window.getCurrentUserId();
            if (userId) {
                console.log(`[RECONNECTION] Re-registering web viewer for user_id: ${userId}`);
                // Re-send check_agent_connection to re-register this web viewer's new SID
                this.socket.emit('check_agent_connection', { user_id: userId });
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

    _setupPageUnloadHandler() {
        // Ensure clean disconnect when page is closed or refreshed
        window.addEventListener('beforeunload', () => {
            console.log('Page unloading - disconnecting socket');
            if (this.socket && this.socket.connected) {
                // Disconnect immediately without reconnection
                this.socket.disconnect();
            }
        });

        // Also handle visibilitychange for better mobile support
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                console.log('Page hidden - socket may disconnect');
                // Socket.IO will handle this automatically, but log for debugging
            } else if (document.visibilityState === 'visible') {
                console.log('Page visible - socket should reconnect if needed');
            }
        });
    }

    // Public method to manually disconnect (e.g., when user logs out)
    disconnect() {
        if (this.socket && this.socket.connected) {
            console.log('Manually disconnecting socket');
            this.socket.disconnect();
        }
    }
}
