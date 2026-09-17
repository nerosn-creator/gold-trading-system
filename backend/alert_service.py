import os
import json
import time
import tempfile
import threading
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import pytz

logger = logging.getLogger("FirstBankAlertService")

# Storage paths (compatible with local & serverless fallback)
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alert_settings.json")
TMP_SETTINGS_FILE = os.path.join(tempfile.gettempdir(), "alert_settings.json")

def get_kh_time_str() -> str:
    try:
        tz = pytz.timezone('Asia/Taipei')
        return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def default_alert_settings() -> Dict[str, Any]:
    return {
        "enabled": False,
        "bot_token": "",
        "chat_id": "",
        "unit": "gram",             # "gram" (新臺幣/公克) 或 "chien" (新臺幣/台錢)
        "target_price": 4400.0,     # 目標買進價格
        "comparison": "lte",        # "lte": 賣出價 <= 目標價 (逢低買進); "gte": 賣出價 >= 目標價
        "cooldown_minutes": 30,     # 觸發後防洗版冷卻時間 (分鐘)
        "quiet_hours_enabled": True,# 夜間勿擾模式 (預設 18:00 ~ 08:00 不通知)
        "quiet_hours_start": "18:00",
        "quiet_hours_end": "08:00",
        "last_triggered_at": None,
        "last_triggered_price": None,
        "history": []
    }

def is_in_quiet_hours(settings: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Checks if current Taipei time falls within quiet hours (default: 18:00 ~ 08:00 next day).
    """
    if not settings.get("quiet_hours_enabled", True):
        return False, ""

    start_str = settings.get("quiet_hours_start", "18:00") or "18:00"
    end_str = settings.get("quiet_hours_end", "08:00") or "08:00"

    try:
        tz = pytz.timezone('Asia/Taipei')
        now_dt = datetime.now(tz)
    except Exception:
        now_dt = datetime.now()

    try:
        start_h, start_m = map(int, start_str.strip().split(":"))
        end_h, end_m = map(int, end_str.strip().split(":"))

        curr_val = now_dt.hour * 60 + now_dt.minute
        start_val = start_h * 60 + start_m
        end_val = end_h * 60 + end_m

        # If start_val > end_val, spans across midnight (e.g. 18:00 -> 08:00)
        if start_val > end_val:
            in_quiet = (curr_val >= start_val or curr_val < end_val)
        else:
            in_quiet = (start_val <= curr_val < end_val)

        if in_quiet:
            return True, f"目前為夜間勿擾時段 ({start_str} ~ 隔天 {end_str})，暫停發送通知"
        return False, ""
    except Exception as e:
        logger.error(f"Failed to parse quiet hours: {e}")
        return False, ""

_memory_settings: Optional[Dict[str, Any]] = None

def load_alert_settings() -> Dict[str, Any]:
    global _memory_settings
    default_cfg = default_alert_settings()
    
    # 1. Base from repository SETTINGS_FILE
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                default_cfg.update(saved)
        except Exception as e:
            logger.error(f"Failed to read alert settings from {SETTINGS_FILE}: {e}")

    # 2. Serverless/local runtime override from TMP_SETTINGS_FILE
    if os.path.exists(TMP_SETTINGS_FILE):
        try:
            with open(TMP_SETTINGS_FILE, "r", encoding="utf-8") as f:
                tmp_saved = json.load(f)
                default_cfg.update(tmp_saved)
        except Exception as e:
            logger.error(f"Failed to read alert settings from {TMP_SETTINGS_FILE}: {e}")

    # 3. Active in-memory override (highest priority)
    if _memory_settings is not None:
        default_cfg.update(_memory_settings)

    return default_cfg

def save_alert_settings(settings: Dict[str, Any]) -> bool:
    global _memory_settings
    _memory_settings = dict(settings)
    saved = False
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        saved = True
    except Exception as e:
        logger.warning(f"Cannot save settings to {SETTINGS_FILE} (expected on serverless): {e}")

    # Always write to TMP_SETTINGS_FILE as well for runtime persistence
    try:
        with open(TMP_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        saved = True
    except Exception as e:
        logger.error(f"Cannot save settings to {TMP_SETTINGS_FILE}: {e}")

    return saved

def send_telegram_message(bot_token: str, chat_id: str, message: str, parse_mode: str = "HTML") -> Tuple[bool, str]:
    """
    Sends message via Telegram Bot API.
    """
    if not bot_token or not chat_id:
        return False, "Bot Token 與 Chat ID 不能為空！"

    url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
    payload = {
        "chat_id": str(chat_id).strip(),
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        data = res.json()
        if res.status_code == 200 and data.get("ok"):
            return True, "Telegram 訊息發送成功！"
        else:
            err_desc = data.get("description", f"HTTP {res.status_code}")
            return False, f"Telegram API 錯誤: {err_desc}"
    except Exception as e:
        logger.error(f"Telegram network request failed: {e}")
        return False, f"連線異常: {str(e)}"

def send_test_telegram(bot_token: str, chat_id: str) -> Tuple[bool, str]:
    """
    Sends a test ping to verify user's Telegram credentials.
    """
    now_time = get_kh_time_str()
    settings = load_alert_settings()
    q_status = f"已啟用 ({settings.get('quiet_hours_start', '18:00')} ~ 隔天 {settings.get('quiet_hours_end', '08:00')} 暫停推播)" if settings.get("quiet_hours_enabled", True) else "未啟用"

    msg = (
        f"<b>🔔 【第一銀行黃金存摺 警報系統測試】</b>\n\n"
        f"恭喜！您的 Telegram Bot 已成功連線至<b>黃金交易量化系統</b>。\n\n"
        f"• <b>測試時間</b>: {now_time}\n"
        f"• <b>連線狀態</b>: 正常在線 (Online)\n"
        f"• <b>夜間勿擾保護</b>: {q_status}\n"
        f"• <b>說明</b>: 當第一銀行黃金賣出價達到您設定的買進門檻時，機器人將立即在此推播通知。\n\n"
        f"<i>💡 溫馨提醒：請保持此對話開啟，隨時接收最新行情通知。</i>"
    )
    return send_telegram_message(bot_token, chat_id, msg)

def evaluate_and_notify(rates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Evaluates current First Bank gold rates against user alert settings.
    If conditions are met, outside quiet hours and cooldown, sends Telegram notification.
    """
    settings = load_alert_settings()
    if not settings.get("enabled"):
        return None

    bot_token = settings.get("bot_token", "")
    chat_id = settings.get("chat_id", "")
    if not bot_token or not chat_id:
        return None

    unit = settings.get("unit", "gram")
    target_price = float(settings.get("target_price", 0.0))
    comparison = settings.get("comparison", "lte")
    cooldown_minutes = float(settings.get("cooldown_minutes", 30))

    if target_price <= 0:
        return None

    # 第一銀行黃金存摺牌價:
    # 投資人「買進」黃金，適用第一銀行的「賣出價」
    if unit == "usd_oz":
        current_price = float(rates.get("usd_gold_sell", 0))
        unit_label = "美元 / 盎司"
        unit_name = "美元/盎司"
        curr_symbol = "$"
    elif unit == "chien":
        current_price = float(rates.get("chien_sell", 0))
        unit_label = "元 / 台錢"
        unit_name = "台錢"
        curr_symbol = "NT$ "
    else:
        current_price = float(rates.get("gram_sell", 0))
        unit_label = "元 / 公克"
        unit_name = "公克"
        curr_symbol = "NT$ "

    if current_price <= 0:
        return None

    # Condition check
    condition_met = False
    condition_text = ""
    target_str = f"{target_price:,.2f}" if unit == "usd_oz" else f"{target_price:,.0f}"
    if comparison == "lte":
        if current_price <= target_price:
            condition_met = True
            condition_text = f"≤ 目標價 {curr_symbol}{target_str} (逢低買進時機)"
    else:
        if current_price >= target_price:
            condition_met = True
            condition_text = f"≥ 目標價 {curr_symbol}{target_str}"

    if not condition_met:
        return None

    # Check Quiet Hours (夜間勿擾限制: 預設 18:00 ~ 隔天 08:00 不發通知)
    in_quiet, quiet_desc = is_in_quiet_hours(settings)
    if in_quiet:
        logger.info(f"Price condition met but notification withheld during quiet hours: {quiet_desc}")
        return None

    # Check Cooldown
    now_ts = time.time()
    last_triggered_ts = settings.get("last_triggered_timestamp", 0)
    cooldown_seconds = cooldown_minutes * 60

    if now_ts - last_triggered_ts < cooldown_seconds:
        # Still in cooldown, avoid spamming
        return None

    # Trigger Notification!
    now_time = get_kh_time_str()
    if unit == "usd_oz":
        bank_buy = rates.get("usd_gold_buy", 0)
        curr_str = f"${current_price:,.2f}"
        buy_str = f"${bank_buy:,.2f}"
    elif unit == "chien":
        bank_buy = rates.get("chien_buy", 0)
        curr_str = f"NT$ {current_price:,.0f}"
        buy_str = f"NT$ {bank_buy:,.0f}"
    else:
        bank_buy = rates.get("gram_buy", 0)
        curr_str = f"NT$ {current_price:,.0f}"
        buy_str = f"NT$ {bank_buy:,.0f}"

    spread = rates.get("spread", 0)
    usd_buy = rates.get("usd_spot_buy", "--")
    usd_sell = rates.get("usd_spot_sell", "--")

    quiet_note = ""
    if settings.get("quiet_hours_enabled", True):
        q_start = settings.get("quiet_hours_start", "18:00")
        q_end = settings.get("quiet_hours_end", "08:00")
        quiet_note = f"🌙 <b>夜間勿擾保護</b>: {q_start} ~ 次日 {q_end} 靜音\n"

    msg = (
        f"🚨 <b>【第一銀行黃金存摺 買進價格觸發通知】</b>\n\n"
        f"🎯 <b>觸發條件</b>: 銀行賣出價 {condition_text}\n"
        f"💰 <b>一銀最新賣出價</b>: <b>{curr_str}</b> {unit_label}\n"
        f"🏦 <b>一銀最新買入價</b>: {buy_str} {unit_label}\n"
        f"📊 <b>新臺幣牌價價差</b>: NT$ {spread:,.0f} / 公克\n"
        f"💵 <b>一銀美元即期匯率</b>: 買入 {usd_buy} / 賣出 {usd_sell}\n"
        f"⏰ <b>觸發時間</b>: {now_time}\n"
        f"{quiet_note}\n"
        f"👉 <b>行動建議</b>: 目前價格已達您預設的買進目標，可至 <a href=\"https://mobile.firstbank.com.tw/c1/cheetah/zh/07/gold/rate?channel=X\">第一銀行行動網銀</a> 辦理黃金存摺買進！\n\n"
        f"<i>（系統已進入 {cooldown_minutes:.0f} 分鐘冷卻期，避免重複推播）</i>"
    )

    success, err_msg = send_telegram_message(bot_token, chat_id, msg)

    # Record history
    history_entry = {
        "timestamp": now_time,
        "unit": unit_name,
        "current_price": current_price,
        "target_price": target_price,
        "comparison": comparison,
        "success": success,
        "detail": "發送成功" if success else err_msg
    }

    settings["last_triggered_at"] = now_time
    settings["last_triggered_timestamp"] = now_ts
    settings["last_triggered_price"] = current_price
    
    hist = settings.get("history", [])
    hist.insert(0, history_entry)
    settings["history"] = hist[:20]  # Keep last 20 records
    save_alert_settings(settings)

    return history_entry

# Background Monitor Thread
_monitor_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()

def alert_monitor_worker():
    """
    Background worker that runs periodically to check First Bank rates and trigger alerts.
    """
    from firstbank_gold import fetch_firstbank_gold_rates
    logger.info("First Bank Gold Alert Monitor worker started.")
    
    # Run loop
    while not _stop_event.is_set():
        try:
            settings = load_alert_settings()
            if settings.get("enabled"):
                rates = fetch_firstbank_gold_rates()
                evaluate_and_notify(rates)
        except Exception as e:
            logger.error(f"Error in alert_monitor_worker: {e}")

        # Sleep in short increments to allow graceful shutdown (e.g. check every 60s)
        for _ in range(60):
            if _stop_event.is_set():
                break
            time.sleep(1)

def start_alert_monitor():
    global _monitor_thread
    if _monitor_thread is not None and _monitor_thread.is_alive():
        return
    _stop_event.clear()
    _monitor_thread = threading.Thread(target=alert_monitor_worker, daemon=True, name="FirstBankAlertMonitor")
    _monitor_thread.start()
    logger.info("FirstBankAlertMonitor background thread launched.")

def stop_alert_monitor():
    _stop_event.set()
