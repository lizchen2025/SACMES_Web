# SACMES Agent v4.0 - 使用指南

**版本**: 4.0 Final
**发布日期**: 2025-10-22
**关键改进**: Registry自动清理 + 路径问题修复

---

## 🎯 v4.0 解决的问题

### 你遇到的问题
1. ❌ **第一次安装成功，第二次失败** - Registry残留导致
2. ❌ **管理员模式运行报错** - 路径问题
3. ❌ **没有详细错误日志** - 难以诊断问题
4. ✅ **需要tkinter支持** - 必须使用完整安装器

### v4.0 的解决方案
✅ **自动Registry清理** - 安装前自动删除冲突记录
✅ **路径修复** - 使用 %~dp0，无论在哪里运行都能找到文件
✅ **详细输出** - 屏幕和日志文件双重记录
✅ **新诊断工具** - diagnose.bat 帮助快速发现问题
✅ **完整tkinter支持** - 使用full installer

---

## 📦 包含的文件

```
SACMES_Agent.zip (93.67 KB)
├── agent.py                    # Agent源码
├── start_agent.bat            # 主启动器 (已修复路径)
├── install_python.bat         # v4.0安装器 (Registry清理)
├── test_installation.bat      # 安装验证
├── diagnose.bat              # 诊断工具 (新!)
├── Netzlab.ico               # 图标
└── README.txt                # 用户文档
```

---

## 🚀 使用步骤

### 首次安装

1. **解压ZIP文件**
   ```
   解压到任意位置，比如：
   C:\SACMES_Agent\
   ```

2. **运行 start_agent.bat**
   - 双击运行 start_agent.bat
   - 或右键 → 以管理员身份运行 (推荐，用于Registry清理)

3. **观察安装过程**
   ```
   ========================================
   SACMES Agent - Setup v4.0
   ========================================

   Script directory: C:\SACMES_Agent\
   Working directory: C:\SACMES_Agent\

   [STEP 1] Checking for existing installation...
   No complete installation found.

   [STEP 2] Cleaning Previous Registry Entries
   ========================================

   This prevents "Modify/Repair/Uninstall" dialog...
   Searching for conflicting registry entries...

   Scanning registry locations...

   No conflicts found!
   Clean start - no previous installations detected.
   Scanned 5 registry locations.

   [STEP 3] Downloading Python 3.11.9
   ========================================

   Downloading full installer with tkinter...
   Connecting to python.org...
   Download complete!

   [STEP 4] Installing Python
   ========================================

   Installing Python (this may take 2-3 minutes)...
   Installation successful!
   Testing tkinter...
   tkinter OK
   tkinter is working!

   [STEP 5] Installing Required Packages
   ========================================

   Installing python-socketio and requests...
   All imports OK

   Installation Complete!
   ```

4. **验证安装**
   - 运行 `test_installation.bat`
   - 应该看到所有检查都是OK

---

## 🔧 重新安装（你的场景）

### 场景：第一次成功，想再次安装

**旧版本（v3.x）的问题**:
```
第一次: 成功 ✓
删除文件夹 ✓
第二次: Registry残留 → "Modify/Repair/Uninstall" 对话框 ✗
```

**v4.0 的解决**:
```
第一次: 成功 ✓
删除文件夹 ✓
第二次:
  [STEP 2] Registry清理 ← 新增！
    找到残留记录
    自动删除
  继续安装 ✓
第二次: 成功 ✓
```

### 操作步骤

1. **删除旧文件夹**
   ```batch
   rmdir /s /q C:\SACMES_Agent\sacmes_python
   rmdir /s /q C:\SACMES_Agent\python_embed  # 如果存在
   ```

2. **运行 start_agent.bat**
   - 推荐：右键 → 以管理员身份运行
   - 这样Registry清理更彻底

3. **观察STEP 2输出**
   ```
   [STEP 2] Cleaning Previous Registry Entries

   FOUND CONFLICT:
     Registry: HKCU:\Software\...\Python311
     Location: C:\SACMES_Agent\sacmes_python
     STATUS: Removed successfully

   Registry cleanup complete!
   Old installation records have been removed.
   ```

4. **安装继续**
   - 不会出现"Modify/Repair"对话框
   - 正常安装到完成

---

## 🛠️ 诊断工具

### diagnose.bat - 新工具！

**什么时候用**:
- 安装失败时
- 想知道当前状态
- 检查Registry是否有冲突
- 推送到服务器前验证

### 运行诊断

```batch
# 双击运行
diagnose.bat

# 或命令行
cd C:\SACMES_Agent
diagnose.bat
```

### 诊断输出示例

```
========================================
SACMES Agent Diagnostic Tool
========================================

Current time: 2025-10-22 18:30:00
Script location: C:\SACMES_Agent\
Working directory: C:\SACMES_Agent\
Running as: Administrator

========================================
FILE CHECK
========================================

Required files:
[OK] agent.py
[OK] start_agent.bat
[OK] install_python.bat
[OK] test_installation.bat

========================================
PYTHON INSTALLATION CHECK
========================================

[EXISTS] sacmes_python folder
[OK] python.exe found
[OK] Python works
Python 3.11.9
[OK] tkinter available
tkinter OK
[OK] python-socketio installed
[OK] requests installed

========================================
REGISTRY CHECK
========================================

Scanning for Python installation records...

No Python-related registry entries found.
Registry is clean!

========================================
LOG FILES
========================================

[EXISTS] install_log.txt
Size: 4821 bytes
Modified: 2025-10-22 18:25:30

Last 10 lines of install_log.txt:
----------------------------------------
[STEP 5] Installing packages
Installing python-socketio requests
Successfully installed python-socketio-5.10.0 requests-2.31.0
All imports OK
Installation completed successfully!
----------------------------------------

========================================
RECOMMENDATIONS
========================================

Installation appears complete!
You can run start_agent.bat to launch the agent.

========================================
Diagnostic complete!
========================================
```

### 如果发现问题

诊断工具会显示：

```
ISSUE DETECTED:
Registry contains conflicting Python installation records.

SOLUTION:
1. Run install_python.bat as Administrator
   (Right-click install_python.bat -> Run as administrator)
2. This will clean the registry and reinstall Python

OR manually clean registry and delete these folders:
- sacmes_python
- python_embed (if exists)
Then run start_agent.bat again
```

---

## 📋 install_log.txt 日志

**位置**: 与agent.py同一目录
**创建**: 每次运行install_python.bat时

**日志内容**:
```
===== SACMES Agent Installation Log =====
Time: 2025-10-22 18:25:15
Script Directory: C:\SACMES_Agent\
Working Directory: C:\SACMES_Agent\
Target Directory: C:\SACMES_Agent\sacmes_python
Unique ID: 12345-67890
==========================================

[STEP 1] Checking existing installation

[STEP 2] Cleaning registry
Found conflicting entry: ...
Removed successfully

[STEP 3] Download
Download URL: https://www.python.org/ftp/python/3.11.9/...
Download OK

[STEP 4] Installing
Installing to temporary location: ...
Installation OK

[STEP 5] Installing packages
Installing python-socketio requests
Successfully installed ...
```

---

## 🧪 测试流程（用于你的环境）

### 测试重复安装

```batch
# 1. 首次安装
cd C:\SACMES_Agent
start_agent.bat
# 等待完成

# 2. 验证
test_installation.bat
# 应该全部OK

# 3. 删除（模拟你的场景）
rmdir /s /q sacmes_python

# 4. 再次安装（关键测试！）
start_agent.bat
# 观察STEP 2 - 应该清理Registry
# 不应该弹出"Modify/Repair"对话框
# 应该成功安装

# 5. 验证
test_installation.bat
# 再次全部OK

# 6. 诊断
diagnose.bat
# 检查是否有Registry残留
```

### 测试管理员模式

```batch
# 右键点击 start_agent.bat
# 选择 "以管理员身份运行"
# 应该看到: "Running as: Administrator"
# 应该正常工作，不报错
```

---

## 📊 STEP 2 Registry清理详解

### 扫描位置

```
HKCU:\Software\Python\PythonCore\3.11
HKLM:\Software\Python\PythonCore\3.11
HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall
HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall
HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall
```

### 查找条件

```powershell
InstallLocation 包含:
- 'sacmes_python'
- 'python_embed'
```

### 删除动作

```
找到匹配 → 尝试删除
成功 → 绿色显示 "Removed successfully"
失败 → 红色显示错误，建议以管理员运行
```

---

## 🔍 故障排除

### 问题1: 仍然出现"Modify/Repair"对话框

**原因**: Registry清理需要管理员权限

**解决**:
```
1. 关闭对话框（点X）
2. 右键 install_python.bat
3. 选择 "以管理员身份运行"
4. 观察STEP 2应该成功删除Registry
```

### 问题2: "install_python.bat not found"

**原因**: 管理员模式下路径不对（已在v4.0修复）

**验证修复**:
```
运行 start_agent.bat 应该显示:
Working directory: C:\SACMES_Agent\
Calling installer from: C:\SACMES_Agent\install_python.bat
```

### 问题3: 下载失败

**症状**:
```
ERROR downloading Python:
The remote server returned an error: (403) Forbidden.
```

**解决**:
```
1. 检查网络连接
2. 临时禁用防火墙/杀毒软件
3. 或手动下载:
   https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
   放到agent目录
   再次运行install_python.bat
```

### 问题4: tkinter不可用

**检查**:
```
sacmes_python\python.exe -c "import tkinter; print('OK')"
```

**如果失败**:
```
说明安装了embeddable版本（没有tkinter）
删除sacmes_python文件夹
确保install_python.bat是v4.0版本
重新运行start_agent.bat
```

---

## 📤 推送到Git和服务器

### 确保最新ZIP

每次修改后重新打包：
```powershell
cd e:\SACMES_web\web\SACMES_Web-Multiuser
.\create_agent_package.ps1
```

### 验证ZIP内容

```powershell
# 查看ZIP文件信息
Get-Item .\SACMES_Agent.zip | Select-Object Name, Length, LastWriteTime

# 解压并验证
Expand-Archive -Path .\SACMES_Agent.zip -DestinationPath .\test_extract -Force
dir .\test_extract
```

### Git提交

```bash
git add SACMES_Agent.zip
git add install_python.bat
git add start_agent.bat
git add diagnose.bat
git add create_agent_package.ps1
git add AGENT_V4.0_GUIDE.md
git commit -m "Agent v4.0: Registry cleanup + path fixes + diagnostics"
git push
```

### 服务器部署

确保服务器上的下载链接指向：
```
https://your-server.com/static/SACMES_Agent.zip
或
https://github.com/your-repo/releases/latest/download/SACMES_Agent.zip
```

---

## ✅ v4.0 检查清单

部署前验证：

- [ ] ZIP文件是最新的（93.67 KB）
- [ ] 包含diagnose.bat（新文件）
- [ ] start_agent.bat使用%~dp0路径
- [ ] install_python.bat是v4.0（有Registry清理）
- [ ] 在干净机器上测试首次安装
- [ ] 测试重复安装（删除文件夹后再安装）
- [ ] 测试管理员模式运行
- [ ] 验证tkinter可用
- [ ] 运行diagnose.bat检查状态
- [ ] install_log.txt正确生成

---

## 📝 版本对比

| 特性 | v3.1 | v4.0 |
|------|------|------|
| 安装方式 | Embeddable only | Full installer |
| tkinter支持 | ❌ 无 | ✅ 有 |
| Registry清理 | ❌ 无 | ✅ 自动 |
| 管理员模式 | ⚠️ 路径错误 | ✅ 正常 |
| 诊断工具 | ❌ 无 | ✅ diagnose.bat |
| 详细日志 | ⚠️ 简单 | ✅ 详细带颜色 |
| 重复安装 | ❌ 失败 | ✅ 成功 |
| 下载大小 | 11 MB | 30 MB |

---

## 🎉 总结

**v4.0完全解决了你遇到的问题**:

1. ✅ **Registry残留** → 自动清理
2. ✅ **第二次安装失败** → 现在成功
3. ✅ **管理员模式错误** → 路径修复
4. ✅ **没有详细日志** → 屏幕+文件双重记录
5. ✅ **需要tkinter** → 使用完整安装器
6. ✅ **难以诊断** → 新增diagnose.bat

**现在可以安全地部署到服务器！**
