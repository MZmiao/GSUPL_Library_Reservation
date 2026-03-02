import os
import requests
import datetime
import json
import re
import time
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from apscheduler.schedulers.blocking import BlockingScheduler

# ────────────────────────────────────────────────
#               配置区（最重要部分）
# ────────────────────────────────────────────────
CONFIG = {
    "username": os.getenv("LIBRARY_USERNAME", ""),          # 学号
    "password_base64": os.getenv("LIBRARY_PASS_BASE64", ""), # base64编码后的密码
    "sender_email": os.getenv("NOTIFY_EMAIL", ""),
    "sender_password": os.getenv("NOTIFY_EMAIL_AUTH", ""),   # QQ邮箱授权码
    "receiver_email": os.getenv("NOTIFY_EMAIL", ""),         # 通常自己收

    # 座位相关参数（需要你抓包更新，可能每学期/每年变）
    "seats": {
        "morning": {   # 07:00 - 13:50
            "roomno": "你的roomno",
            "tableid": "你的tableid",
            "tableno": "座位号，例如 051",
            "beskid": "122",
            "beskCanId": "70",
            "begintime": "07:00:00",
            "endtime": "13:50:00"
        },
        "afternoon": {  # 13:50 - 22:30
            "roomno": "你的roomno",
            "tableid": "你的tableid",
            "tableno": "座位号，例如 051",
            "beskid": "103",
            "beskCanId": "69",
            "begintime": "13:50:02",
            "endtime": "22:30:00"
        }
    }
}

LOGIN_URL = "https://seat.gsupl.edu.cn/你的登录接口"           # ← 替换
YUYUE_URL = "https://seat.gsupl.edu.cn/readingroom/postbeskdata"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Host': 'seat.gsupl.edu.cn',
    'Referer': 'https://seat.gsupl.edu.cn/'
}

# ────────────────────────────────────────────────
#               初始化 requests session + 重试
# ────────────────────────────────────────────────
def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1.2, status_forcelist=[502, 503, 504, 429])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update(HEADERS)
    return session

# ────────────────────────────────────────────────
#                  登录
# ────────────────────────────────────────────────
def login(session):
    if not CONFIG["username"] or not CONFIG["password_base64"]:
        print("缺少用户名或密码环境变量！")
        return False

    params = {
        'url': 'index',
        'user': CONFIG["username"],
        'passwd': CONFIG["password_base64"]
    }
    try:
        r = session.post(LOGIN_URL, params=params, timeout=10)
        if r.status_code != 200:
            print(f"登录请求失败 {r.status_code}")
            return False

        # 这里可以加更严格的判断，比如检查是否出现“欢迎”或 token 等
        if "退出" in r.text or "个人信息" in r.text:
            print("登录成功")
            return True
        else:
            print("登录可能失败，返回内容不包含预期标志")
            return False
    except Exception as e:
        print(f"登录异常: {e}")
        return False

# ────────────────────────────────────────────────
#               简单检查 session 是否仍然有效
# ────────────────────────────────────────────────
def is_session_valid(session):
    try:
        # 随便访问一个需要登录的页面，例如个人预约记录
        r = session.get("https://seat.gsupl.edu.cn/你的某个需要登录的页面", timeout=8)
        return r.status_code == 200 and "退出" in r.text
    except:
        return False

# ────────────────────────────────────────────────
#                  预约核心函数
# ────────────────────────────────────────────────
def try_reserve(session, is_afternoon: bool) -> tuple[bool, str]:
    field = "afternoon" if is_afternoon else "morning"
    params = CONFIG["seats"][field].copy()

    try:
        r = session.post(YUYUE_URL, params=params, timeout=12)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"

        data = r.json()
        msg = data.get("Msg", "无返回消息")

        if data.get("ReturnValue") == 0:
            return True, msg
        else:
            return False, msg
    except Exception as e:
        return False, f"异常: {str(e)}"

# ────────────────────────────────────────────────
#               发送邮件
# ────────────────────────────────────────────────
def send_email(success: bool, message: str = "", attempts: int = 0):
    if not all([CONFIG["sender_email"], CONFIG["sender_password"], CONFIG["receiver_email"]]):
        print("邮件配置不完整，跳过发送")
        return

    subject = "【图书馆座位】预约成功！" if success else "【图书馆座位】预约失败"
    body = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    body += f"尝试次数：{attempts}\n"
    body += f"结果：{message}\n\n"
    body += "请尽快确认！" if success else "请检查脚本/参数/网络"

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = CONFIG["sender_email"]
    msg['To'] = CONFIG["receiver_email"]

    try:
        server = smtplib.SMTP_SSL('smtp.qq.com', 465, timeout=15)
        server.login(CONFIG["sender_email"], CONFIG["sender_password"])
        server.sendmail(CONFIG["sender_email"], [CONFIG["receiver_email"]], msg.as_string())
        print("邮件发送成功")
    except Exception as e:
        print(f"邮件发送失败：{e}")
    finally:
        if 'server' in locals():
            server.quit()

# ────────────────────────────────────────────────
#               解析服务器返回的“请X分X秒后重试”
# ────────────────────────────────────────────────
def parse_retry_time(text: str) -> int:
    # 常见格式： "请01分23秒后重试" 或 "操作太频繁，请稍后再试"
    pattern = r'(\d{1,2})分(\d{1,2})秒'
    m = re.search(pattern, text)
    if m:
        minutes = int(m.group(1))
        seconds = int(m.group(2))
        return minutes * 60 + seconds - 2  # 提前2秒再尝试
    return -1  # 未匹配到时间

# ────────────────────────────────────────────────
#               核心预约逻辑
# ────────────────────────────────────────────────
def job_func():
    now = datetime.datetime.now()
    print(f"\n========== {now.strftime('%Y-%m-%d %H:%M:%S')} 开始执行 =========")

    hour = now.hour
    is_afternoon = hour >= 13   # 13:00 后抢下午场，否则抢上午场

    session = create_session()

    # 登录（或重登录）
    if not login(session):
        send_email(False, "登录失败")
        return

    max_attempts = 40
    attempt = 0

    while attempt < max_attempts:
        attempt += 1
        success, msg = try_reserve(session, is_afternoon)

        print(f"第 {attempt} 次尝试 → {msg}")

        if success:
            send_email(True, msg, attempt)
            print("预约成功！结束本次任务")
            return

        # 判断是否 session 失效
        if "未登录" in msg or "请重新登录" in msg:
            print("检测到登录失效，重新登录...")
            if not login(session):
                send_email(False, "重新登录失败")
                return
            time.sleep(2)
            continue

        # 解析冷却时间
        wait_sec = parse_retry_time(msg)
        if wait_sec > 0:
            print(f"服务器要求等待 ≈ {wait_sec} 秒")
            time.sleep(min(wait_sec, 120))   # 最多等2分钟，防止异常长等待
        else:
            # 其他错误，短睡
            time.sleep(3)

    # 达到最大尝试次数仍失败
    send_email(False, "超过最大尝试次数仍未成功", attempt)

# ────────────────────────────────────────────────
#               定时任务
# ────────────────────────────────────────────────
if __name__ == "__main__":
    print("程序启动，计划每天 7:59 和 16:59 开始抢座")

    # 检查关键环境变量是否存在
    required_env = ["LIBRARY_USERNAME", "LIBRARY_PASS_BASE64"]
    missing = [k for k in required_env if not os.getenv(k)]
    if missing:
        print("缺少环境变量：", ", ".join(missing))
        print("请先设置 export LIBRARY_USERNAME=... 等")
        exit(1)

    scheduler = BlockingScheduler()
    scheduler.add_job(job_func, 'cron', hour='7,16', minute=59, second=3)  # 稍错开几秒避免同时冲突
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("程序被手动终止")
