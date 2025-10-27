# 部署前检查清单

## 准备推送到GitHub和部署到OpenShift

### ✅ 已完成的工作

1. **多用户架构 (100% 完成)**
   - [x] Server端user_id映射系统
   - [x] Agent端User ID显示和发送
   - [x] Web端User ID输入界面
   - [x] 所有socket emissions包含user_id
   - [x] 错误处理和验证

2. **代码清理**
   - [x] 更新.gitignore排除本地构建文件
   - [x] 排除SACMES_Agent/文件夹
   - [x] 排除所有.bat构建脚本
   - [x] 排除临时文档和测试文件

3. **文档**
   - [x] IMPLEMENTATION_COMPLETE.md
   - [x] MULTI_USER_SERVER_COMPLETE.md
   - [x] WEB_FRONTEND_COMPLETE.md
   - [x] DEPLOYMENT_GUIDE.md
   - [x] USER_ID_MIGRATION_STATUS.md

---

## 📋 推送到GitHub前的检查

### 代码质量检查
- [ ] 所有Python语法正确（运行 `python -m py_compile app.py agent.py`）
- [ ] 所有JavaScript语法正确
- [ ] 没有硬编码的密码或密钥
- [ ] 环境变量正确配置

### Git检查
```bash
# 查看当前分支
git branch

# 查看将要提交的文件
git status

# 查看具体修改内容
git diff --cached

# 确认没有不应该提交的文件
git ls-files | grep -E "SACMES_Agent|\.bat$|\.exe$"
```

### 需要排除的文件（已在.gitignore中）
- ✅ SACMES_Agent/
- ✅ *.bat (构建脚本)
- ✅ *.exe, *.msi
- ✅ build/, dist/
- ✅ 临时文档
- ✅ 测试文件

### 需要保留的文件
- ✅ app.py
- ✅ agent.py
- ✅ agent.json
- ✅ requirements.txt
- ✅ static/ (所有web资源)
- ✅ templates/ (如果有)
- ✅ data_processing/
- ✅ README.md
- ✅ 部署相关文档

---

## 🚀 推送步骤

### 1. 本地提交

```bash
# 确认在正确的分支
git branch
# 应该显示: * userid

# 查看修改
git status

# 提交更改
git commit -m "Prepare for production deployment

- Update .gitignore to exclude local build files and SACMES_Agent/
- Add comprehensive OpenShift deployment guide
- Multi-user architecture ready for production
- All documentation updated

Ready for production testing on OpenShift
"
```

### 2. 推送到GitHub

```bash
# 推送当前分支
git push origin userid

# 如果需要，创建production分支
git checkout -b production
git push origin production
```

### 3. 验证推送成功

访问GitHub仓库，确认：
- [ ] .gitignore已更新
- [ ] DEPLOYMENT_GUIDE.md存在
- [ ] 没有SACMES_Agent/文件夹
- [ ] 没有.bat构建脚本
- [ ] static/downloads/SACMES_Agent.zip存在（这个应该保留）

---

## 🔧 OpenShift部署步骤

### 快速部署（推荐）

按照 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) 中的"快速部署命令总结"部分执行。

### 最小化部署命令

```bash
# 1. 登录OpenShift
oc login <your-cluster-url>

# 2. 创建项目
oc new-project sacmes-multiuser

# 3. 部署Redis（必需）
oc new-app redis:6 --name=redis -e REDIS_PASSWORD=<生成一个强密码>

# 4. 部署SACMES Web应用
oc new-app python:3.11~https://github.com/<your-username>/<your-repo>.git#userid \
  --name=sacmes-web \
  -e FLASK_ENV=production \
  -e REDIS_HOST=redis \
  -e REDIS_PORT=6379 \
  -e REDIS_PASSWORD=<与上面相同的密码>

# 5. 暴露服务
oc expose svc/sacmes-web

# 6. 启用HTTPS
oc create route edge --service=sacmes-web --insecure-policy=Redirect

# 7. 获取访问URL
oc get route sacmes-web -o jsonpath='{.spec.host}'
```

---

## 🧪 部署后测试清单

### 基础功能测试
1. [ ] 访问应用URL，页面正常加载
2. [ ] Socket.IO连接成功（检查浏览器控制台）
3. [ ] Redis连接正常（检查应用日志）

### 多用户功能测试
1. [ ] 启动本地Agent A
2. [ ] 启动本地Agent B（可以在另一台电脑）
3. [ ] 浏览器窗口1：输入Agent A的User ID，连接成功
4. [ ] 浏览器窗口2：输入Agent B的User ID，连接成功
5. [ ] 窗口1启动SWV分析，查看数据
6. [ ] 窗口2启动CV分析，查看数据
7. [ ] 验证窗口1只显示Agent A的数据
8. [ ] 验证窗口2只显示Agent B的数据
9. [ ] 两个窗口分别导出数据，验证数据正确

### 错误处理测试
1. [ ] 输入无效的User ID格式，显示错误
2. [ ] 输入不存在的User ID，显示"Agent not found"
3. [ ] 未连接就尝试开始分析，显示提示
4. [ ] Agent断开连接，显示警告

### 性能测试
1. [ ] 3-5个用户同时使用，系统稳定
2. [ ] 大量数据分析时，系统响应正常
3. [ ] 页面刷新后，User ID自动填充（localStorage）

---

## 📊 监控重点

### 部署后需要监控的指标

```bash
# 查看应用日志
oc logs -f deployment/sacmes-web

# 查看资源使用
oc adm top pods

# 查看Pod状态
oc get pods -w
```

### 关键日志模式

**成功的连接：**
```
AGENT connected. User ID: xxx-xxx-xxx, SID: yyy, Session: zzz
Registered agent user: xxx-xxx-xxx
```

**错误需要注意：**
```
No active agent session found for user_id
Redis connection error
Socket.IO connection failed
```

---

## 🔒 安全检查

### 生产环境必须：
- [ ] 使用HTTPS（OpenShift Route配置）
- [ ] Redis密码设置强密码
- [ ] SECRET_KEY使用随机生成的值
- [ ] 禁用DEBUG模式（FLASK_ENV=production）
- [ ] 限制CORS来源（如果需要）

### 生成安全密钥

```python
# 生成SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# 生成REDIS_PASSWORD
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 📝 环境变量清单

### 必需的环境变量

```bash
FLASK_ENV=production
SECRET_KEY=<随机生成的密钥>
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<强密码>
```

### 可选的环境变量

```bash
LOG_LEVEL=INFO
SOCKETIO_MESSAGE_QUEUE=redis://:password@redis:6379/0
```

---

## 🆘 常见问题排查

### 问题1: 应用无法启动
**检查：**
```bash
oc logs deployment/sacmes-web
oc describe pod <pod-name>
```

### 问题2: Redis连接失败
**检查：**
```bash
oc logs deployment/redis
oc exec deployment/sacmes-web -- python -c "import redis; r=redis.Redis(host='redis', port=6379); print(r.ping())"
```

### 问题3: Socket.IO连接问题
**检查：**
- 浏览器控制台错误
- CORS配置
- WebSocket支持
- 代理/防火墙设置

### 问题4: 多用户数据混淆
**检查：**
- Redis是否正常运行
- user_id是否正确传递
- 查看服务器日志中的user_id

---

## ✅ 最终检查

部署前最后确认：

1. **代码检查**
   - [ ] .gitignore正确配置
   - [ ] 没有敏感信息
   - [ ] 所有文档更新

2. **推送检查**
   - [ ] 代码已提交
   - [ ] 已推送到GitHub
   - [ ] 分支正确

3. **部署准备**
   - [ ] OpenShift访问权限
   - [ ] Redis密码准备好
   - [ ] 部署命令准备好

4. **测试准备**
   - [ ] 测试Agent准备好
   - [ ] 测试账号准备好
   - [ ] 测试数据准备好

---

## 📞 支持资源

- **部署指南**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **架构文档**: [MULTI_USER_SERVER_COMPLETE.md](MULTI_USER_SERVER_COMPLETE.md)
- **实现总结**: [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)
- **OpenShift文档**: https://docs.openshift.com/

---

**准备就绪！可以开始推送和部署了！** 🚀

*检查清单创建时间: 2025-10-27*
