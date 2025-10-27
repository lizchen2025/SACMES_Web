# SACMES Multi-User Deployment Guide

## OpenShift部署指南

---

## 前提条件

- [x] 代码已推送到GitHub
- [ ] 有OpenShift访问权限
- [ ] 已安装oc命令行工具
- [ ] Redis服务可用（推荐）

---

## 1. 准备GitHub仓库

### 提交并推送更改

```bash
# 查看当前状态
git status

# 添加所有修改（.gitignore已配置好排除本地文件）
git add .

# 提交修改
git commit -m "Add multi-user support with user_id-based architecture

- Implemented user_id mapping system for multi-user support
- Added User ID input interface in web frontend
- Updated all socket handlers to use user_id
- Added connection verification endpoint
- Enhanced error handling for user_id validation
- Added comprehensive documentation

Fixes: Multi-user conflicts
Features: Unlimited simultaneous users with data isolation
"

# 推送到GitHub（确保在正确的分支）
git push origin userid
```

### 创建Production分支（可选）

```bash
# 从当前分支创建production分支
git checkout -b production

# 推送到GitHub
git push origin production
```

---

## 2. OpenShift部署配置

### 方式一：使用OpenShift Web Console

1. **登录OpenShift Console**
   - 访问你的OpenShift控制台
   - 创建新项目：`sacmes-multiuser`

2. **部署应用**
   - 点击 "Add" → "From Git"
   - 输入GitHub仓库URL
   - 选择分支：`userid` 或 `production`
   - Builder Image：选择 `Python`
   - Python版本：`3.11` 或 `3.10`
   - 应用名称：`sacmes-web`

3. **配置环境变量**
   ```
   FLASK_ENV=production
   REDIS_HOST=<your-redis-host>
   REDIS_PORT=6379
   REDIS_PASSWORD=<your-redis-password>
   SECRET_KEY=<generate-a-random-secret-key>
   ```

4. **配置资源限制**
   ```yaml
   resources:
     limits:
       cpu: "1000m"
       memory: "512Mi"
     requests:
       cpu: "100m"
       memory: "256Mi"
   ```

5. **创建Route**
   - 名称：`sacmes-web`
   - TLS：启用 (推荐)
   - Termination: Edge

### 方式二：使用oc命令行

```bash
# 登录OpenShift
oc login <your-openshift-cluster-url>

# 创建项目
oc new-project sacmes-multiuser

# 从GitHub部署应用
oc new-app python:3.11~https://github.com/<your-username>/<your-repo>.git#userid \
  --name=sacmes-web \
  -e FLASK_ENV=production \
  -e REDIS_HOST=<redis-host> \
  -e REDIS_PORT=6379

# 暴露服务
oc expose svc/sacmes-web

# 启用HTTPS
oc create route edge sacmes-web --service=sacmes-web --insecure-policy=Redirect
```

---

## 3. Redis部署（推荐）

### 在OpenShift中部署Redis

```bash
# 部署Redis
oc new-app redis:6 --name=redis -e REDIS_PASSWORD=<your-password>

# 创建持久化存储（可选）
oc set volume deployment/redis \
  --add --name=redis-data \
  --type=persistentVolumeClaim \
  --claim-name=redis-pvc \
  --mount-path=/data

# 更新SACMES应用环境变量
oc set env deployment/sacmes-web \
  REDIS_HOST=redis \
  REDIS_PORT=6379 \
  REDIS_PASSWORD=<your-password>
```

### 或使用外部Redis服务

```bash
# 配置外部Redis
oc set env deployment/sacmes-web \
  REDIS_HOST=<external-redis-host> \
  REDIS_PORT=6379 \
  REDIS_PASSWORD=<password>
```

---

## 4. 配置文件调整

### 创建OpenShift配置文件

创建 `.openshift/` 目录（如果不存在）：

```bash
mkdir -p .openshift
```

### 创建 requirements.txt

确保 `requirements.txt` 包含所有依赖：

```txt
Flask==2.3.3
Flask-SocketIO==5.3.4
python-socketio==5.9.0
python-engineio==4.7.1
eventlet==0.33.3
redis==5.0.0
numpy==1.24.3
scipy==1.11.2
```

### 创建 .s2i/environment

创建 `.s2i/environment` 文件：

```bash
# 创建目录
mkdir -p .s2i

# 创建文件
cat > .s2i/environment << 'EOF'
# Python configuration
ENABLE_PIPENV=false
UPGRADE_PIP_TO_LATEST=true
WEB_CONCURRENCY=1

# Application settings
APP_MODULE=app:app
APP_FILE=app.py
EOF
```

### 创建 Procfile（可选）

创建 `Procfile` 文件：

```
web: gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8080 app:app
```

---

## 5. 环境变量配置

### 必需的环境变量

```bash
# 应用配置
FLASK_ENV=production
SECRET_KEY=<generate-random-key>

# Redis配置（推荐）
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<your-password>

# Socket.IO配置
SOCKETIO_MESSAGE_QUEUE=redis://:password@redis:6379/0
```

### 可选的环境变量

```bash
# 日志级别
LOG_LEVEL=INFO

# CORS配置（如果需要）
CORS_ORIGINS=https://your-domain.com

# 会话超时
SESSION_TIMEOUT=3600
```

---

## 6. 健康检查配置

### 添加健康检查端点

在 `app.py` 中添加（如果还没有）：

```python
@app.route('/health')
def health():
    """Health check endpoint for OpenShift"""
    return {'status': 'healthy'}, 200

@app.route('/ready')
def ready():
    """Readiness check endpoint"""
    # Check Redis connection
    if redis_client:
        try:
            redis_client.ping()
            return {'status': 'ready'}, 200
        except:
            return {'status': 'not ready', 'reason': 'Redis unavailable'}, 503
    return {'status': 'ready'}, 200
```

### 配置OpenShift健康检查

```bash
# Liveness probe
oc set probe deployment/sacmes-web \
  --liveness \
  --get-url=http://:8080/health \
  --initial-delay-seconds=30 \
  --period-seconds=10

# Readiness probe
oc set probe deployment/sacmes-web \
  --readiness \
  --get-url=http://:8080/ready \
  --initial-delay-seconds=10 \
  --period-seconds=5
```

---

## 7. CORS配置（如果需要）

如果你的前端和后端在不同的域名，需要配置CORS：

在 `app.py` 中添加：

```python
from flask_cors import CORS

# 配置CORS
CORS(app, resources={
    r"/*": {
        "origins": ["https://your-frontend-domain.com"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

---

## 8. 扩展和负载均衡

### 横向扩展（多个Pod）

```bash
# 扩展到3个副本
oc scale deployment/sacmes-web --replicas=3
```

**注意：多副本需要Redis作为消息队列！**

### 配置自动扩展

```bash
# 创建HPA (Horizontal Pod Autoscaler)
oc autoscale deployment/sacmes-web \
  --min=2 \
  --max=10 \
  --cpu-percent=70
```

---

## 9. 监控和日志

### 查看应用日志

```bash
# 查看实时日志
oc logs -f deployment/sacmes-web

# 查看特定Pod的日志
oc logs <pod-name>

# 查看之前的日志
oc logs <pod-name> --previous
```

### 查看应用状态

```bash
# 查看所有资源
oc get all

# 查看Pod状态
oc get pods

# 查看部署详情
oc describe deployment/sacmes-web

# 查看环境变量
oc set env deployment/sacmes-web --list
```

### 进入Pod调试

```bash
# 进入Pod shell
oc rsh deployment/sacmes-web

# 在Pod中执行命令
oc exec <pod-name> -- python -c "import redis; print('Redis OK')"
```

---

## 10. SSL/TLS配置

### 启用HTTPS

```bash
# 创建带TLS的Route
oc create route edge sacmes-web \
  --service=sacmes-web \
  --insecure-policy=Redirect \
  --hostname=sacmes.your-domain.com
```

### 使用自定义证书（可选）

```bash
# 创建带自定义证书的Route
oc create route edge sacmes-web \
  --service=sacmes-web \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  --ca-cert=path/to/ca.crt \
  --hostname=sacmes.your-domain.com
```

---

## 11. 部署验证清单

部署完成后，验证以下内容：

### 基础功能
- [ ] 应用可以访问（https://your-app-url）
- [ ] 健康检查端点正常（/health, /ready）
- [ ] Socket.IO连接成功
- [ ] Redis连接正常（如果使用）

### 多用户功能
- [ ] 用户可以输入User ID
- [ ] 连接验证正常工作
- [ ] 两个用户可以同时连接不同的agent
- [ ] 数据隔离正确（用户A看不到用户B的数据）
- [ ] 导出功能包含正确的user_id
- [ ] 断开连接处理正常

### 性能和稳定性
- [ ] 页面加载速度正常
- [ ] Socket.IO没有频繁断开重连
- [ ] 内存使用稳定
- [ ] CPU使用正常
- [ ] 多用户并发测试通过

---

## 12. 故障排查

### 应用无法启动

```bash
# 查看Pod事件
oc describe pod <pod-name>

# 查看构建日志
oc logs -f bc/sacmes-web

# 检查环境变量
oc set env deployment/sacmes-web --list
```

### Redis连接失败

```bash
# 测试Redis连接
oc exec deployment/sacmes-web -- python -c "
import redis
r = redis.Redis(host='redis', port=6379, password='your-password')
print(r.ping())
"

# 检查Redis状态
oc logs deployment/redis
```

### Socket.IO连接问题

1. 检查CORS配置
2. 确认WebSocket支持
3. 查看浏览器控制台错误
4. 检查防火墙/代理设置

### 性能问题

```bash
# 查看资源使用
oc adm top pods

# 增加资源限制
oc set resources deployment/sacmes-web \
  --limits=cpu=2000m,memory=1Gi \
  --requests=cpu=500m,memory=512Mi
```

---

## 13. 回滚和更新

### 更新应用

```bash
# 触发新的构建
oc start-build sacmes-web

# 或者推送新代码到GitHub（如果配置了webhook）
git push origin userid
```

### 回滚到上一个版本

```bash
# 查看部署历史
oc rollout history deployment/sacmes-web

# 回滚到上一个版本
oc rollout undo deployment/sacmes-web

# 回滚到特定版本
oc rollout undo deployment/sacmes-web --to-revision=2
```

---

## 14. 安全建议

### 环境变量安全

```bash
# 使用Secret存储敏感信息
oc create secret generic sacmes-secrets \
  --from-literal=SECRET_KEY=<your-secret-key> \
  --from-literal=REDIS_PASSWORD=<redis-password>

# 将Secret挂载为环境变量
oc set env deployment/sacmes-web --from=secret/sacmes-secrets
```

### 网络策略

```bash
# 限制入站流量（示例）
oc create -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sacmes-network-policy
spec:
  podSelector:
    matchLabels:
      app: sacmes-web
  ingress:
  - from:
    - podSelector: {}
    ports:
    - protocol: TCP
      port: 8080
EOF
```

---

## 15. 备份和恢复

### 备份Redis数据

```bash
# 创建Redis数据快照
oc exec deployment/redis -- redis-cli SAVE

# 导出数据
oc rsync <redis-pod>:/data ./redis-backup/
```

### 恢复数据

```bash
# 复制备份数据到Redis Pod
oc rsync ./redis-backup/ <redis-pod>:/data

# 重启Redis
oc rollout restart deployment/redis
```

---

## 16. 生产环境最佳实践

1. **使用Redis**
   - 必须配置Redis用于session存储和消息队列
   - 启用Redis持久化

2. **启用HTTPS**
   - 所有生产环境必须使用HTTPS
   - 配置HTTP到HTTPS重定向

3. **设置资源限制**
   - 合理配置CPU和内存限制
   - 避免资源耗尽

4. **配置健康检查**
   - Liveness probe检测应用是否存活
   - Readiness probe检测应用是否就绪

5. **监控和告警**
   - 监控应用性能指标
   - 设置告警规则

6. **备份策略**
   - 定期备份Redis数据
   - 保留部署配置

7. **更新策略**
   - 使用滚动更新
   - 保留历史版本便于回滚

---

## 快速部署命令总结

```bash
# 1. 推送代码到GitHub
git add .
git commit -m "Multi-user support deployment"
git push origin userid

# 2. 登录OpenShift
oc login <cluster-url>

# 3. 创建项目
oc new-project sacmes-multiuser

# 4. 部署Redis
oc new-app redis:6 --name=redis -e REDIS_PASSWORD=yourpassword

# 5. 部署应用
oc new-app python:3.11~https://github.com/your-username/your-repo.git#userid \
  --name=sacmes-web \
  -e FLASK_ENV=production \
  -e REDIS_HOST=redis \
  -e REDIS_PORT=6379 \
  -e REDIS_PASSWORD=yourpassword

# 6. 暴露服务
oc expose svc/sacmes-web

# 7. 启用HTTPS
oc create route edge --service=sacmes-web --insecure-policy=Redirect

# 8. 配置健康检查
oc set probe deployment/sacmes-web --liveness --get-url=http://:8080/health
oc set probe deployment/sacmes-web --readiness --get-url=http://:8080/ready

# 9. 查看应用URL
oc get route sacmes-web
```

---

## 支持和帮助

- OpenShift文档: https://docs.openshift.com/
- 查看应用日志: `oc logs -f deployment/sacmes-web`
- 进入Pod调试: `oc rsh deployment/sacmes-web`

---

*部署指南更新时间: 2025-10-27*
