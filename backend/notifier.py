import requests
import logging
from typing import Dict, Any

logger = logging.getLogger("GoldNotifier")

def send_alert_notification(signal_data: Dict[str, Any], webhook_url: str = None) -> bool:
    """
    Sends signal alert notification to configured webhooks (e.g. Telegram / LINE Notify).
    """
    symbol = signal_data.get("symbol", "XAU/USD")
    price = signal_data.get("current_price", 0.0)
    sig_type = signal_data.get("signal_type", "NEUTRAL")
    score = signal_data.get("signal_score", 0)
    tp = signal_data.get("take_profit", 0.0)
    sl = signal_data.get("stop_loss", 0.0)
    reasons = "\n• ".join(signal_data.get("reasons", []))

    msg = f"🔔 【黃金量化訊號警報】\n" \
          f"標的: {symbol}\n" \
          f"最新價格: ${price:.2f}\n" \
          f"訊號類型: {sig_type} (評分: {score:+d})\n" \
          f"建議止盈(TP): ${tp:.2f}\n" \
          f"建議止損(SL): ${sl:.2f}\n" \
          f"觸發條件:\n• {reasons}"

    logger.info(f"Generated alert message:\n{msg}")

    if webhook_url:
        try:
            res = requests.post(webhook_url, json={"text": msg}, timeout=5)
            return res.status_code == 200
        except Exception as e:
            logger.error(f"Failed to post alert webhook: {e}")
            return False
    return True
