# SACMES Monitor Mode & Privacy Fix

## 概述

Monitor Mode 允许多台设备使用相同的 User ID 实时监控同一个 Agent 的分析过程。这个功能对于以下场景非常有用：

- 在实验室运行 Agent 进行数据分析，同时在办公室或家里监控进度
- 团队成员协同查看实时分析结果
- 在演示时让多个观众同时查看分析过程

## 重要的隐私修复

本次更新修复了一个**严重的隐私漏洞**：

### 问题描述
在之前的实现中，所有用户的分析数据都会被广播给所有在线的 web viewers，无论他们使用的是哪个 user_id。这意味着：
- 用户A的数据会被发送给用户B、C、D...
- 完全没有数据隔离
- 严重的隐私泄露风险

### 修复方案
现在的实现确保：
- ✅ 每个用户的数据**只发送给**使用相同 user_id 的 web viewers
- ✅ 完全的用户数据隔离
- ✅ 支持多设备 monitor 模式的同时保护隐私

## 技术实现

### 1. 数据结构

添加了新的映射表来跟踪 web viewers：

```python
# app.py
web_user_mapping = {}  # {user_id: set([web_viewer_sid1, web_viewer_sid2, ...])}
```

### 2. 核心函数

#### 注册 Web Viewer
```python
def register_web_viewer_user(user_id, web_viewer_sid):
    """将 web viewer 注册到 user_id，支持多设备监控"""
```

#### 获取用户的所有 Viewers
```python
def get_web_viewers_by_user_id(user_id):
    """获取特定 user_id 的所有 web viewer SIDs"""
```

#### 反向查找
```python
def get_user_id_by_web_viewer_sid(web_viewer_sid):
    """通过 web viewer SID 查找 user_id"""

def get_user_id_by_session_id(session_id):
    """通过 session_id 查找 user_id"""
```

### 3. 修改的关键点

#### (1) 数据广播逻辑 (app.py:886-908)
**修改前**（隐私漏洞）:
```python
# 发送给所有 session 的所有 web viewers
all_web_viewer_sids = []
for session_key in session_keys:
    viewer_sids = get_web_viewers(session_key)
    all_web_viewer_sids.extend(viewer_sids)

socketio.emit('live_analysis_update', data, to=all_web_viewer_sids)
```

**修改后**（隐私保护）:
```python
# 只发送给匹配 user_id 的 web viewers
user_id = get_user_id_by_session_id(session_id)
user_web_viewers = get_web_viewers_by_user_id(user_id)

socketio.emit('live_analysis_update', data, to=user_web_viewers)
logger.info(f"Sent data to {len(user_web_viewers)} viewers for user_id: {user_id}")
```

#### (2) Agent 连接/断开通知 (app.py:1580-1587, 1664-1671)
同样修改为只通知对应 user_id 的 viewers。

#### (3) Web Viewer 连接 (app.py:2560-2578)
在 `check_agent_connection` 成功时注册 web viewer：
```python
if agent_mapping:
    register_web_viewer_user(user_id, request.sid)
    viewer_count = len(get_web_viewers_by_user_id(user_id))
    emit('agent_connection_status', {
        'connected': True,
        'user_id': user_id,
        'viewer_count': viewer_count  # 告知有多少设备在监控
    })
```

#### (4) Web Viewer 断开 (app.py:1684-1688)
清理映射表：
```python
viewer_user_id = get_user_id_by_web_viewer_sid(request.sid)
if viewer_user_id:
    unregister_web_viewer_user(viewer_user_id, request.sid)
```

### 4. 前端显示 (index.html)

添加了 Monitor Mode 指示器：

```html
<!-- Monitor mode indicator -->
<div id="monitorModeIndicator" class="hidden flex items-center gap-2 ml-5">
    <svg class="w-4 h-4 text-blue-500">...</svg>
    <span id="monitorModeText" class="text-xs text-blue-600 font-medium"></span>
</div>
```

JavaScript 逻辑：
```javascript
const viewerCount = response.viewer_count || 1;
if (viewerCount > 1) {
    monitorText.textContent = `Monitor Mode: ${viewerCount} devices viewing`;
    monitorIndicator.classList.remove('hidden');
}
```

## 使用场景

### 场景 1: 实验室 + 办公室监控

```
实验室电脑A:
1. 运行 agent.exe → 获得 User ID: abc123
2. 打开浏览器 → 输入 abc123 → 开始 SWV 分析
3. 查看实时结果

办公室电脑B (同时):
1. 打开浏览器 → 输入 abc123
2. 自动进入 Monitor Mode
3. 实时看到电脑A的分析进度
4. 显示 "Monitor Mode: 2 devices viewing"
```

### 场景 2: 团队协作

```
团队成员A (数据采集):
- 运行 Agent，采集数据
- User ID: xyz789

团队成员B, C, D (远程监控):
- 各自在不同电脑上输入 xyz789
- 同时查看实时分析结果
- 显示 "Monitor Mode: 4 devices viewing"
```

### 场景 3: 演示/教学

```
讲师电脑:
- 运行 Agent 进行演示分析
- User ID: demo001

学生设备 (10台):
- 全部输入 demo001
- 实时查看讲师的分析过程
- 显示 "Monitor Mode: 11 devices viewing"
```

## 隐私保证

### 数据隔离验证

```
用户A (user_id: AAA):
- Agent 在电脑1运行
- Web viewer 在电脑2查看
- 只接收 user_id=AAA 的数据 ✅

用户B (user_id: BBB):
- Agent 在电脑3运行
- Web viewer 在电脑4查看
- 只接收 user_id=BBB 的数据 ✅
- 绝不会收到用户A的数据 ✅
```

### Redis 持久化

所有映射关系都存储在 Redis 中：
- `agent_user_mapping`: user_id → agent_sid
- `web_user_mapping`: user_id → [web_viewer_sids]

支持分布式部署和服务器重启后恢复。

## 测试建议

### 测试 1: Monitor 模式功能
1. 启动 Agent (User ID: test123)
2. 在电脑A打开浏览器，输入 test123，连接成功
3. 在电脑B打开浏览器，输入 test123，连接成功
4. 验证两台电脑都显示 "Monitor Mode: 2 devices viewing"
5. 在 Agent 上开始分析
6. 验证两台电脑都能实时看到相同的分析结果

### 测试 2: 隐私隔离
1. 启动 Agent A (User ID: userA)
2. 启动 Agent B (User ID: userB)
3. 电脑1输入 userA，电脑2输入 userB
4. 在 Agent A 上分析数据
5. 验证电脑1能看到结果，电脑2看不到 ✅
6. 在 Agent B 上分析数据
7. 验证电脑2能看到结果，电脑1看不到 ✅

### 测试 3: 断开清理
1. 多台设备连接到同一个 user_id
2. 逐个断开设备
3. 验证 viewer_count 正确递减
4. 验证服务器日志正确清理映射

## 日志示例

成功的 Monitor 模式日志：

```
[INFO] Registered web viewer: user_id=abc123, sid=xyz789, total_viewers=1
[INFO] Web viewer xyz789 registered to user_id: abc123, total viewers: 1

[INFO] Registered web viewer: user_id=abc123, sid=def456, total_viewers=2
[INFO] Web viewer def456 registered to user_id: abc123, total viewers: 2

[INFO] Sent analysis update to 2 web viewers for user_id: abc123
```

隐私保护日志：

```
[INFO] Sent analysis update to 2 web viewers for user_id: abc123
[INFO] Sent analysis update to 1 web viewers for user_id: xyz789
[WARNING] Could not find user_id for session: old-session-123 - skipping broadcast for privacy
```

## 版本信息

- **功能**: Monitor Mode & Privacy Fix
- **日期**: 2025-10-27
- **影响文件**:
  - `app.py`: 添加 web_user_mapping 和相关函数
  - `static/index.html`: 添加 Monitor Mode UI 显示
- **向后兼容**: 完全兼容，现有功能不受影响
- **安全性**: 修复了严重的隐私泄露漏洞

## 后续优化建议

1. **权限控制** (可选)
   - 区分"控制者"和"监控者"角色
   - 只允许第一个连接的设备控制分析参数

2. **状态同步**
   - 新加入的 monitor 自动获取当前进度
   - 从 Redis 加载已有的 trend_data

3. **实时通知**
   - 当新设备加入时，通知其他设备
   - 显示每个设备的连接时间和位置

4. **监控统计**
   - 记录每个 user_id 的监控历史
   - 生成使用报告

---

**重要**: 这个更新不仅添加了新功能，更重要的是修复了一个严重的隐私漏洞。建议立即部署到生产环境。
