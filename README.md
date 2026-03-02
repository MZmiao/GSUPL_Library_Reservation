# 图书馆座位自动预约脚本

这是一个用于自动预约（gsupl）图书馆座位的Python脚本，支持定时执行、失败重试、登录状态检测和邮件通知功能。

## 功能特点
- 🕒 **定时预约**：支持每天定点自动执行预约任务
- 🔄 **自动重试**：预约失败时自动重试，并解析服务器冷却时间
- 🔐 **登录保活**：检测登录状态失效时自动重新登录
- 📧 **邮件通知**：预约成功/失败后自动发送邮件提醒
- 🛡️ **网络容错**：内置请求重试机制，应对网络波动

## 环境要求
- Python 3.7+
- 所需依赖包：
  ```bash
  pip install requests apscheduler urllib3

### 1. 环境变量配置（推荐）
为了安全，建议通过环境变量设置敏感信息：

  ```bash
# Linux/Mac
export LIBRARY_USERNAME="你的学号"
export LIBRARY_PASS_BASE64="base64编码后的密码"
export NOTIFY_EMAIL="你的QQ邮箱地址"
export NOTIFY_EMAIL_AUTH="QQ邮箱授权码"

# Windows (PowerShell)
$env:LIBRARY_USERNAME="你的学号"
$env:LIBRARY_PASS_BASE64="base64编码后的密码"
$env:NOTIFY_EMAIL="你的QQ邮箱地址"
$env:NOTIFY_EMAIL_AUTH="QQ邮箱授权码"


### 2. 脚本内部配置
需要替换脚本中以下关键配置项：

| 配置项 | 说明 |
|--------|------|
| `LOGIN_URL` | 图书馆系统的登录接口 URL（需抓包获取） |
| `is_session_valid` 中的检查 URL | 需要登录才能访问的页面 URL（如个人预约记录页） |
| `CONFIG["seats"]` 下的参数 | 座位相关参数（roomno/tableid 等，需抓包获取） |

#### 座位参数获取方法
1. 打开浏览器开发者工具（F12）→ 切换到 Network（网络）标签
2. 手动预约座位，找到预约请求（postbeskdata）
3. 从请求参数中复制：roomno、tableid、tableno、beskid、beskCanId
4. 替换脚本中对应的值

### 3. 定时任务配置
脚本默认配置：
- 每天 7:59:03 执行上午场预约（07:00-13:50）
- 每天 16:59:03 执行下午场预约（13:50-22:30）

如需修改时间，调整以下代码：
```python
scheduler.add_job(job_func, 'cron', hour='7,16', minute=59, second=3)


- `hour`：小时（24 小时制）
- `minute`：分钟
- `second`：秒

## 使用方法
### 直接运行
```bash
python library_seat_reserve.py


### 后台运行
```bash
nohup python library_seat_reserve.py > reserve.log 2>&1 &

### 查看日志
```bash
tail -f reserve.log

## 常见问题
### Q1: 登录失败怎么办？
- 检查学号和 base64 编码的密码是否正确
- 确认登录接口 URL 是否正确（可能学校系统更新）
- 检查网络是否能正常访问图书馆预约系统

### Q2: 预约失败提示 "操作太频繁"？
- 这是服务器限制，脚本已内置冷却时间解析，会自动等待后重试
- 可适当调整 max_attempts（最大尝试次数）参数

### Q3: 邮件发送失败？
- 确认 QQ 邮箱已开启 SMTP 服务
- 检查授权码是否正确（不是邮箱登录密码）
- 确认网络能访问 smtp.qq.com:465

### Q4: 定时任务不执行？
- 检查系统时间是否正确
- 确认 apscheduler 库已正确安装
- 查看日志是否有报错信息

## 注意事项
- 请勿过度频繁请求，遵守学校系统使用规则
- 建议设置合理的重试间隔，避免给服务器造成压力
- 定期检查脚本运行状态，学校系统接口可能会更新
- 脚本仅用于个人学习和便利使用，请勿用于商业用途

## 免责声明
本脚本仅为学习交流使用，因使用本脚本产生的任何问题（如账号封禁、预约规则违反等），均由使用者自行承担责任。
