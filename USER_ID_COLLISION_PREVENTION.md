# User ID Collision Prevention (用户ID冲突防护)

## 安全问题说明

### 之前存在的漏洞 (已修复)

**问题描述**：
在之前的实现中，如果两个Agent使用了相同的user_id（无论是UUID巧合还是恶意攻击），后连接的Agent会**直接覆盖**前一个Agent的映射，导致：

1. **数据劫持**：恶意用户可以故意使用别人的user_id，接管数据流
2. **用户断连**：第一个用户会突然失去连接
3. **隐私泄露**：第二个用户可以看到第一个用户的分析结果

**风险等级**：🔴 高危

### UUID冲突概率

虽然UUID v4冲突概率极低：
- 理论冲突概率：约 1/(2^122) ≈ 1/5.3×10^36
- 实际意义：生成10亿个UUID，冲突概率仍然接近0

但这**不能防御恶意攻击**！

## 当前的防护机制 (已实施)

### 1. 服务器端冲突检测

当Agent尝试连接时，服务器会检查user_id是否已被占用：

```python
# app.py: handle_connect()
existing_agent = get_agent_session_by_user_id(user_id)
if existing_agent:
    # User ID collision detected - reject connection
    logger.error(f"SECURITY: User ID collision detected! user_id={user_id}")
    emit('connection_rejected', {
        'reason': 'user_id_collision',
        'message': 'User ID is already in use. Please restart your agent.',
        'user_id': user_id
    })
    return False  # Reject connection
```

### 2. 连接拒绝流程

```
Agent A (user_id: abc123)
    ↓
连接成功 → 注册到 agent_user_mapping
    ↓
开始分析

Agent B (user_id: abc123) ← 相同的user_id！
    ↓
尝试连接 → 服务器检测到冲突
    ↓
连接被拒绝 ← 收到 'connection_rejected' 事件
    ↓
Agent显示错误：需要重启生成新ID
```

### 3. 安全日志

服务器会记录所有冲突尝试：

```
[ERROR] SECURITY: User ID collision detected! user_id=abc123 is already in use by agent_sid=xyz789
[ERROR] Rejecting new connection attempt from sid=def456
```

## Agent端需要的修改

### 必需：处理连接拒绝事件

Agent需要监听 `connection_rejected` 事件：

```python
# agent.py

@sio.on('connection_rejected')
def on_connection_rejected(data):
    reason = data.get('reason')
    message = data.get('message')
    user_id = data.get('user_id')

    if reason == 'user_id_collision':
        print("\n" + "="*60)
        print("❌ ERROR: User ID Collision Detected")
        print("="*60)
        print(f"Your User ID ({user_id}) is already in use by another agent.")
        print("\nPossible causes:")
        print("1. You have another instance of this agent running")
        print("2. Extremely rare UUID collision (probability: 1/10^36)")
        print("3. Someone is maliciously using your User ID")
        print("\nSolution:")
        print("→ Please RESTART this agent to generate a new User ID")
        print("="*60 + "\n")

        # Disconnect and exit
        sio.disconnect()
        sys.exit(1)
```

### 可选：断线重连逻辑

如果需要支持Agent断线重连（使用相同user_id）：

**方案A：时间窗口**
```python
# 允许5秒内重连（同一user_id）
if existing_agent:
    disconnected_at = existing_agent.get('disconnected_at')
    if disconnected_at and (datetime.now() - disconnected_at).seconds < 5:
        # 允许重连
        logger.info(f"Agent reconnecting with user_id: {user_id}")
        # 覆盖旧映射
    else:
        # 拒绝连接
```

**方案B：Session验证**
```python
# Agent保存session_id，重连时提供
if existing_agent:
    old_session_id = existing_agent.get('session_id')
    reconnect_session_id = request.args.get('reconnect_session_id')

    if reconnect_session_id == old_session_id:
        # 同一个Agent重连，允许
        logger.info(f"Agent reconnecting: {user_id}")
    else:
        # 不同Agent，拒绝
```

## 防护效果

### ✅ 防御的攻击场景

1. **恶意user_id复用**
   ```
   攻击者获取他人的user_id → 尝试连接 → 被拒绝 ✅
   ```

2. **意外的重复启动**
   ```
   用户忘记关闭Agent，又启动一个 → 第二个被拒绝 ✅
   提示用户检查已运行的实例
   ```

3. **极端罕见的UUID冲突**
   ```
   两个Agent恰好生成相同UUID → 后者被拒绝 ✅
   重启后生成新UUID，问题解决
   ```

### ❌ 无法防御的场景

1. **中间人攻击**
   - 如果攻击者能拦截网络流量，获取user_id和token
   - 建议：使用HTTPS + 额外的客户端证书认证

2. **Agent端被攻破**
   - 如果攻击者控制了Agent本身
   - 建议：代码签名 + 完整性检查

## 测试方案

### 测试1：正常冲突拒绝

```bash
# Terminal 1
python agent.py
# 记录显示的 User ID: abc123

# Terminal 2 (模拟冲突)
# 修改agent.py硬编码使用 user_id='abc123'
python agent.py

# 预期结果：
# Terminal 2 连接被拒绝，显示错误信息
```

### 测试2：连续启动

```bash
# 快速连续启动两个agent
python agent.py &
python agent.py &

# 预期结果：
# 两个都成功（user_id不同）
```

### 测试3：日志验证

```bash
# 服务器日志应包含：
[ERROR] SECURITY: User ID collision detected! user_id=abc123 is already in use
[ERROR] Rejecting new connection attempt from sid=...
```

## 监控和告警

### 建议的监控指标

1. **冲突频率**
   - 正常情况：几乎为0
   - 异常情况：频繁冲突 → 可能是攻击

2. **同一user_id的重复尝试**
   - 短时间内多次尝试 → 可能是暴力攻击
   - 建议：添加IP封禁

3. **user_id重用模式**
   - 追踪哪些user_id被重复使用
   - 分析是否有规律（攻击特征）

### 告警规则示例

```python
# 添加到app.py

collision_attempts = {}  # {user_id: [timestamp1, timestamp2, ...]}

def check_collision_attack(user_id):
    now = datetime.now()
    if user_id not in collision_attempts:
        collision_attempts[user_id] = []

    # 清理10分钟前的记录
    collision_attempts[user_id] = [
        t for t in collision_attempts[user_id]
        if (now - t).seconds < 600
    ]

    collision_attempts[user_id].append(now)

    # 10分钟内超过5次 → 告警
    if len(collision_attempts[user_id]) > 5:
        logger.critical(f"SECURITY ALERT: Possible attack on user_id {user_id}")
        # 发送邮件/Slack通知
```

## 额外的安全建议

### 1. 增强User ID唯一性

除了UUID，可以结合其他信息：

```python
import hashlib
import uuid
import platform

def generate_unique_user_id():
    # UUID v4基础
    base_uuid = str(uuid.uuid4())

    # 添加机器特征（可选）
    machine_info = f"{platform.node()}-{uuid.getnode()}"  # 主机名+MAC地址
    enhanced_id = f"{base_uuid}-{hashlib.sha256(machine_info.encode()).hexdigest()[:8]}"

    return enhanced_id
```

### 2. 客户端指纹

```python
# 记录Agent的指纹信息
agent_fingerprint = {
    'user_id': user_id,
    'hostname': socket.gethostname(),
    'platform': platform.system(),
    'python_version': platform.python_version(),
    'first_seen': datetime.now()
}

# 如果相同user_id但指纹不同 → 拒绝
```

### 3. 定期轮换User ID

```python
# Agent定期（如每24小时）重新生成user_id
# 降低长期劫持的风险
```

## 版本历史

- **v1.0** (2025-10-27): 初始实现 - 添加user_id冲突检测和拒绝机制
- **后续计划**:
  - 添加重连逻辑（允许合法的断线重连）
  - 实施攻击检测和自动封禁
  - 添加客户端指纹验证

---

**重要提示**：这个安全机制已经在服务器端实施，但Agent端需要更新以正确处理 `connection_rejected` 事件。请确保Agent代码包含相应的错误处理逻辑。
