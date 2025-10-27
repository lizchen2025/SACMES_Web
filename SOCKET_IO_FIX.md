# Socket.IO Initialization Fix

## 问题描述

用户在网页端输入User ID并点击"Connect to Agent"时，出现错误：
```
Socket.IO not initialized. Please refresh the page.
```

## 根本原因

SACMES项目使用ES6模块化架构，`socket` 对象被封装在 `SocketManager` 类中，不是全局变量。User ID连接代码直接引用了不存在的全局 `socket` 对象。

## 解决方案

### 1. 在 main.js 中暴露 socketManager (Line 16)

```javascript
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Socket Manager
    const socketManager = new SocketManager();

    // Expose socketManager globally for User ID connection functionality
    window.socketManager = socketManager;

    // ... rest of initialization
});
```

### 2. 修改 index.html 中的 connectToAgent() 函数

**修改前:**
```javascript
if (typeof socket === 'undefined') { ... }
socket.emit('check_agent_connection', { ... });
```

**修改后:**
```javascript
if (typeof window.socketManager === 'undefined') { ... }
window.socketManager.emit('check_agent_connection', { ... });
```

### 3. 创建初始化函数等待 socketManager 可用

```javascript
function initializeUserIdSocketListeners() {
    if (!window.socketManager) {
        console.log('Waiting for socketManager...');
        setTimeout(initializeUserIdSocketListeners, 100);
        return;
    }

    // Register event listeners
    window.socketManager.on('agent_connection_status', function(response) { ... });
    window.socketManager.on('agent_status', function(data) { ... });
}
```

### 4. 在 DOMContentLoaded 中调用初始化

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Load saved user_id
    // Disable analysis buttons
    // Initialize socket event listeners
    initializeUserIdSocketListeners();
});
```

## 修改的文件

1. **static/js/main.js**
   - Line 16: 添加 `window.socketManager = socketManager;`

2. **static/index.html**
   - Line 1651: 修改检查为 `window.socketManager`
   - Line 1657: 修改为 `window.socketManager.emit()`
   - Line 1764-1822: 创建 `initializeUserIdSocketListeners()` 函数
   - Line 1623: 在 DOMContentLoaded 中调用初始化函数

## 测试步骤

1. 刷新网页
2. 打开浏览器控制台（F12）
3. 应该看到：`User ID socket listeners initialized`
4. 输入User ID
5. 点击"Connect to Agent"
6. 应该看到：`Verifying agent connection...`
7. 如果agent在线，应该连接成功

## 验证

打开浏览器控制台，执行：
```javascript
console.log(window.socketManager);
// 应该显示 SocketManager 对象

console.log(typeof window.socketManager.emit);
// 应该显示 "function"
```

## 相关文档

- Socket.IO文档: https://socket.io/docs/v4/
- ES6模块: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules

---

*修复时间: 2025-10-27*
*问题已解决: Socket.IO现在可以正常初始化和使用*
