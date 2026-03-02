# 图书馆座位自动预约脚本

这是一个用于自动预约广州工商学院（gsupl）图书馆座位的Python脚本，支持定时执行、失败重试、登录状态检测和邮件通知功能。

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
