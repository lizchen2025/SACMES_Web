# Web Frontend Migration - TODO

## Overview

This document provides step-by-step instructions for migrating the web frontend to support the new user_id-based multi-user architecture.

**Status:** Server-side migration is COMPLETE. Web frontend migration is PENDING.

---

## Prerequisites

Before starting, ensure:
- [x] Server-side migration is complete (see MULTI_USER_SERVER_COMPLETE.md)
- [x] Agent displays user_id and sends it on connection
- [ ] You have backed up templates/index.html
- [ ] You have access to all JavaScript files

---

## Phase 1: Add User ID Input Interface

### Location: `templates/index.html`

### Task 1.1: Add User ID Input Section

Find the welcome section or header area and add a user ID input interface.

**Recommended Location:** Near the top of the page, in a prominent position

**HTML to Add:**
```html
<!-- User ID Connection Section -->
<div id="userIdSection" class="user-id-section">
    <div class="user-id-container">
        <h3>Connect to Your Agent</h3>
        <p class="instruction-text">
            Enter the User ID displayed in your SACMES Agent application:
        </p>

        <div class="user-id-input-group">
            <input
                type="text"
                id="userIdInput"
                placeholder="e.g., abc12345-def6-7890-ghij-klmnopqrstuv"
                class="user-id-input"
            />
            <button id="connectAgentBtn" class="btn-primary">
                Connect to Agent
            </button>
        </div>

        <div id="connectionStatus" class="connection-status hidden">
            <span id="statusIcon" class="status-icon"></span>
            <span id="statusText" class="status-text"></span>
        </div>

        <div id="agentInfo" class="agent-info hidden">
            <p>Connected to Agent: <strong id="connectedUserId"></strong></p>
            <button id="disconnectBtn" class="btn-secondary">Disconnect</button>
        </div>
    </div>
</div>
```

**CSS to Add:**
```css
.user-id-section {
    background-color: #f5f5f5;
    padding: 20px;
    margin: 20px 0;
    border-radius: 8px;
    border: 2px solid #4CAF50;
}

.user-id-container {
    max-width: 600px;
    margin: 0 auto;
}

.user-id-container h3 {
    color: #333;
    margin-bottom: 10px;
}

.instruction-text {
    color: #666;
    font-size: 14px;
    margin-bottom: 15px;
}

.user-id-input-group {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;
}

.user-id-input {
    flex: 1;
    padding: 10px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 14px;
}

.user-id-input:focus {
    outline: none;
    border-color: #4CAF50;
    box-shadow: 0 0 5px rgba(76, 175, 80, 0.3);
}

.btn-primary {
    padding: 10px 20px;
    background-color: #4CAF50;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
}

.btn-primary:hover {
    background-color: #45a049;
}

.btn-primary:disabled {
    background-color: #ccc;
    cursor: not-allowed;
}

.btn-secondary {
    padding: 8px 16px;
    background-color: #f44336;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

.btn-secondary:hover {
    background-color: #da190b;
}

.connection-status {
    padding: 10px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.connection-status.success {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
}

.connection-status.error {
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    color: #721c24;
}

.connection-status.info {
    background-color: #d1ecf1;
    border: 1px solid #bee5eb;
    color: #0c5460;
}

.hidden {
    display: none !important;
}

.agent-info {
    padding: 10px;
    background-color: #e8f5e9;
    border: 1px solid #a5d6a7;
    border-radius: 4px;
    margin-top: 10px;
}

.agent-info p {
    margin: 0 0 10px 0;
    color: #2e7d32;
}

.status-icon {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    display: inline-block;
}

.status-icon.connected {
    background-color: #4CAF50;
}

.status-icon.disconnected {
    background-color: #f44336;
}
```

---

### Task 1.2: Add JavaScript for User ID Management

Add this JavaScript code in the `<script>` section of index.html:

```javascript
// ============================================
// User ID Management
// ============================================

let currentUserId = null;

// Load saved user_id from localStorage on page load
document.addEventListener('DOMContentLoaded', function() {
    const savedUserId = localStorage.getItem('sacmes_user_id');
    if (savedUserId) {
        document.getElementById('userIdInput').value = savedUserId;
        // Auto-connect if user_id was previously used
        // Uncomment the line below if you want auto-connect:
        // connectToAgent(savedUserId);
    }
});

// Connect button click handler
document.getElementById('connectAgentBtn').addEventListener('click', function() {
    const userId = document.getElementById('userIdInput').value.trim();

    if (!userId) {
        showConnectionStatus('error', 'Please enter a User ID');
        return;
    }

    // Basic validation: UUID format
    const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidPattern.test(userId)) {
        showConnectionStatus('error', 'Invalid User ID format. Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx');
        return;
    }

    connectToAgent(userId);
});

// Disconnect button click handler
document.getElementById('disconnectBtn').addEventListener('click', function() {
    disconnectFromAgent();
});

// Connect to agent with user_id
function connectToAgent(userId) {
    showConnectionStatus('info', 'Connecting to agent...');

    // TODO: Implement actual connection check via socket.io
    // For now, we'll just save it and assume it works
    currentUserId = userId;

    // Save to localStorage
    localStorage.setItem('sacmes_user_id', userId);

    // Update UI
    document.getElementById('userIdInput').disabled = true;
    document.getElementById('connectAgentBtn').disabled = true;
    document.getElementById('connectedUserId').textContent = userId;
    document.getElementById('agentInfo').classList.remove('hidden');
    document.getElementById('connectionStatus').classList.add('hidden');

    console.log('Connected to agent with user_id:', userId);

    // Enable analysis controls
    enableAnalysisControls();
}

// Disconnect from agent
function disconnectFromAgent() {
    currentUserId = null;

    // Clear localStorage (optional - you may want to keep it for convenience)
    // localStorage.removeItem('sacmes_user_id');

    // Update UI
    document.getElementById('userIdInput').disabled = false;
    document.getElementById('connectAgentBtn').disabled = false;
    document.getElementById('agentInfo').classList.add('hidden');
    showConnectionStatus('info', 'Disconnected from agent');

    console.log('Disconnected from agent');

    // Disable analysis controls
    disableAnalysisControls();
}

// Show connection status message
function showConnectionStatus(type, message) {
    const statusDiv = document.getElementById('connectionStatus');
    const statusIcon = document.getElementById('statusIcon');
    const statusText = document.getElementById('statusText');

    // Remove previous classes
    statusDiv.className = 'connection-status';
    statusIcon.className = 'status-icon';

    // Add new classes
    statusDiv.classList.add(type);
    if (type === 'success') {
        statusIcon.classList.add('connected');
    } else if (type === 'error') {
        statusIcon.classList.add('disconnected');
    }

    statusText.textContent = message;
    statusDiv.classList.remove('hidden');

    // Auto-hide after 5 seconds for non-error messages
    if (type !== 'error') {
        setTimeout(() => {
            statusDiv.classList.add('hidden');
        }, 5000);
    }
}

// Enable analysis controls (called when connected)
function enableAnalysisControls() {
    // TODO: Enable your start/stop/export buttons
    // Example:
    // document.getElementById('startAnalysisBtn').disabled = false;
    // document.getElementById('exportBtn').disabled = false;
}

// Disable analysis controls (called when disconnected)
function disableAnalysisControls() {
    // TODO: Disable your start/stop/export buttons
    // Example:
    // document.getElementById('startAnalysisBtn').disabled = true;
    // document.getElementById('exportBtn').disabled = true;
}

// Helper function to get current user_id
function getCurrentUserId() {
    return currentUserId;
}

// Helper function to check if connected
function isConnectedToAgent() {
    return currentUserId !== null;
}
```

---

## Phase 2: Update Socket Emissions

### Task 2.1: Identify All Socket Emissions

Search for all instances of `socket.emit()` in your JavaScript code.

**Common events that need user_id:**
- `start_analysis_session`
- `start_cv_analysis_session`
- `start_frequency_map_session`
- `request_export_data`
- `request_export_cv_data`
- `request_export_frequency_map_data`

### Task 2.2: Update Each Socket Emission

**BEFORE:**
```javascript
socket.emit('start_analysis_session', {
    analysisParams: params,
    filters: filters
});
```

**AFTER:**
```javascript
// Check if connected to agent
if (!isConnectedToAgent()) {
    alert('Please connect to an agent first by entering your User ID.');
    return;
}

socket.emit('start_analysis_session', {
    user_id: getCurrentUserId(),  // ADD THIS LINE
    analysisParams: params,
    filters: filters
});
```

### Task 2.3: Update Export Functions

**Example: SWV Export**

**BEFORE:**
```javascript
socket.emit('request_export_data', {
    current_electrode: currentElectrode,
    export_all: exportAll
});
```

**AFTER:**
```javascript
if (!isConnectedToAgent()) {
    alert('Please connect to an agent first.');
    return;
}

socket.emit('request_export_data', {
    user_id: getCurrentUserId(),  // ADD THIS LINE
    current_electrode: currentElectrode,
    export_all: exportAll
});
```

**Example: CV Export**

**BEFORE:**
```javascript
socket.emit('request_export_cv_data', {
    export_all: true
});
```

**AFTER:**
```javascript
if (!isConnectedToAgent()) {
    alert('Please connect to an agent first.');
    return;
}

socket.emit('request_export_cv_data', {
    user_id: getCurrentUserId(),  // ADD THIS LINE
    export_all: true
});
```

**Example: Frequency Map Export**

**BEFORE:**
```javascript
socket.emit('request_export_frequency_map_data', {
    current_electrode: electrode,
    export_all: exportAll
});
```

**AFTER:**
```javascript
if (!isConnectedToAgent()) {
    alert('Please connect to an agent first.');
    return;
}

socket.emit('request_export_frequency_map_data', {
    user_id: getCurrentUserId(),  // ADD THIS LINE
    current_electrode: electrode,
    export_all: exportAll
});
```

---

## Phase 3: Handle Server Responses

### Task 3.1: Update Error Handlers

Add handlers for the new error messages from the server:

```javascript
// Listen for start session acknowledgment
socket.on('ack_start_session', function(response) {
    if (response.status === 'error') {
        if (response.message.includes('User ID')) {
            // User ID related error
            showConnectionStatus('error', response.message);
            alert('Error: ' + response.message + '\nPlease check your User ID and try again.');
        } else {
            // Other errors
            alert('Error: ' + response.message);
        }
    } else {
        // Success
        console.log('Analysis session started successfully');
    }
});

// Similar for CV and Frequency Map
socket.on('ack_start_cv_session', function(response) {
    if (response.status === 'error') {
        if (response.message.includes('User ID')) {
            showConnectionStatus('error', response.message);
            alert('Error: ' + response.message + '\nPlease check your User ID and try again.');
        } else {
            alert('Error: ' + response.message);
        }
    }
});

socket.on('ack_start_frequency_map_session', function(response) {
    if (response.status === 'error') {
        if (response.message.includes('User ID')) {
            showConnectionStatus('error', response.message);
            alert('Error: ' + response.message + '\nPlease check your User ID and try again.');
        } else {
            alert('Error: ' + response.message);
        }
    }
});
```

### Task 3.2: Listen for Agent Status Updates

Add a listener for agent status updates (connection/disconnection):

```javascript
socket.on('agent_status', function(data) {
    console.log('Agent status update:', data);

    // Check if this affects our connected agent
    if (data.user_id === currentUserId) {
        if (data.status === 'disconnected') {
            showConnectionStatus('error', 'Your agent has disconnected');
            alert('Warning: Your agent has disconnected. Please restart your agent and reconnect.');
            // Optionally auto-disconnect
            // disconnectFromAgent();
        } else if (data.status === 'connected') {
            showConnectionStatus('success', 'Your agent is now connected');
        }
    }
});
```

---

## Phase 4: Optional Advanced Features

### Task 4.1: Add Connection Verification

Implement a socket event to verify agent connection:

**Server-side (app.py) - Add this handler:**
```python
@socketio.on('check_agent_connection')
def handle_check_agent_connection(data):
    """Check if agent with given user_id is currently connected."""
    user_id = data.get('user_id')

    if not user_id:
        emit('agent_connection_status', {'status': 'error', 'message': 'User ID required'})
        return

    agent_mapping = get_agent_session_by_user_id(user_id)

    if agent_mapping:
        emit('agent_connection_status', {
            'status': 'success',
            'connected': True,
            'user_id': user_id,
            'connected_at': agent_mapping.get('connected_at')
        })
    else:
        emit('agent_connection_status', {
            'status': 'success',
            'connected': False,
            'user_id': user_id,
            'message': 'No agent found with this User ID'
        })
```

**Client-side (index.html) - Update connectToAgent():**
```javascript
function connectToAgent(userId) {
    showConnectionStatus('info', 'Verifying agent connection...');

    // Emit check connection request
    socket.emit('check_agent_connection', {
        user_id: userId
    });
}

// Add listener for connection check response
socket.on('agent_connection_status', function(response) {
    if (response.status === 'error') {
        showConnectionStatus('error', response.message);
        return;
    }

    if (response.connected) {
        // Agent is connected
        currentUserId = response.user_id;
        localStorage.setItem('sacmes_user_id', response.user_id);

        document.getElementById('userIdInput').disabled = true;
        document.getElementById('connectAgentBtn').disabled = true;
        document.getElementById('connectedUserId').textContent = response.user_id;
        document.getElementById('agentInfo').classList.remove('hidden');

        showConnectionStatus('success', 'Successfully connected to agent!');
        enableAnalysisControls();

        console.log('Connected to agent at:', response.connected_at);
    } else {
        // Agent not found
        showConnectionStatus('error', 'Agent not found. Please check your User ID and ensure your agent is running.');
    }
});
```

### Task 4.2: Add Auto-Reconnect on Page Reload

Add this to the DOMContentLoaded event:

```javascript
document.addEventListener('DOMContentLoaded', function() {
    const savedUserId = localStorage.getItem('sacmes_user_id');
    if (savedUserId) {
        document.getElementById('userIdInput').value = savedUserId;

        // Wait for socket to connect first
        socket.on('connect', function() {
            // Auto-verify connection after 1 second
            setTimeout(() => {
                connectToAgent(savedUserId);
            }, 1000);
        });
    }
});
```

---

## Testing Checklist

### Pre-Testing
- [ ] Backup all files before modification
- [ ] Server is running with multi-user support
- [ ] Agent is running and displaying User ID

### UI Testing
- [ ] User ID input field is visible and styled correctly
- [ ] Connect button works
- [ ] Disconnect button works
- [ ] Connection status messages display correctly
- [ ] User ID is saved to localStorage
- [ ] User ID is loaded from localStorage on page reload

### Functional Testing
- [ ] Start SWV analysis with user_id
- [ ] Start CV analysis with user_id
- [ ] Start Frequency Map analysis with user_id
- [ ] Export SWV data with user_id
- [ ] Export CV data with user_id
- [ ] Export Frequency Map data with user_id
- [ ] Error messages show when user_id is missing
- [ ] Error messages show when agent not found

### Multi-User Testing
- [ ] Open two agents with different user_ids
- [ ] Open two browser windows
- [ ] Connect each browser to a different agent
- [ ] Start analysis in both browsers simultaneously
- [ ] Verify data doesn't mix between sessions
- [ ] Export data from both browsers
- [ ] Verify each export contains correct data

---

## Common Issues and Solutions

### Issue 1: "User ID is required" error
**Cause:** Socket emission missing user_id parameter
**Solution:** Add `user_id: getCurrentUserId()` to the data object

### Issue 2: "No active agent session found for this User ID"
**Cause:** Agent with that user_id is not connected
**Solution:**
1. Check agent is running
2. Check agent connected successfully
3. Verify user_id matches exactly (copy-paste from agent)

### Issue 3: localStorage not persisting
**Cause:** Browser privacy settings
**Solution:** Check browser allows localStorage, or implement cookie-based storage

### Issue 4: UI not updating after connection
**Cause:** JavaScript errors or missing event listeners
**Solution:** Check browser console for errors, ensure all functions are defined

---

## File Modification Summary

| File | Changes | Priority |
|------|---------|----------|
| templates/index.html | Add User ID input UI | HIGH |
| templates/index.html | Add User ID JavaScript | HIGH |
| templates/index.html | Update all socket.emit() | HIGH |
| static/css/main.css | Add User ID styles | MEDIUM |
| static/js/*.js | Update socket emissions | HIGH |
| app.py | Add check_agent_connection handler | OPTIONAL |

---

## Next Steps

1. **Add User ID Input UI** (Phase 1)
   - Add HTML elements
   - Add CSS styling
   - Add JavaScript handlers

2. **Update Socket Emissions** (Phase 2)
   - Find all socket.emit() calls
   - Add user_id to each emission
   - Add validation checks

3. **Test Thoroughly** (Phase 3)
   - Single user test
   - Multi-user test
   - Error handling test

4. **Deploy** (Phase 4)
   - Test in production environment
   - Monitor logs for errors
   - Gather user feedback

---

## Support

For assistance with web frontend migration:
1. Review MULTI_USER_SERVER_COMPLETE.md for server-side architecture
2. Check browser console for JavaScript errors
3. Check server logs for socket event errors
4. Test with curl or Postman to verify server endpoints
