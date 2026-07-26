import os
import time
import threading
import requests
import logging
import sys
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ---------------------------------------------------------
# LOGGING CONFIGURATION
# ---------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# ENVIRONMENT VARIABLES & CONFIGURATIONS
# ---------------------------------------------------------
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

if not API_ID or not API_HASH or not SESSION_STRING:
    logger.error("❌ API_ID, API_HASH သို့မဟုတ် SESSION_STRING မတွေ့ရှိပါ။ Environment Variables တွင် စစ်ဆေးပါ။")
    exit(1)

API_ID = int(API_ID)

# သတ်မှတ်ထားသော Group IDs (Integer ပုံစံသို့ ပြောင်းရန်)
TARGET_CHATS = [-1004295330651, -1003315850707, -1003854698282]

# သင့်ရဲ့ Telegram User ID (Forward လက်ခံမည့်သူ)
ADMIN_USER_ID = 8506436817

# Telethon Client ကို Session String ဖြင့် စတင်ခြင်း
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ---------------------------------------------------------
# FLASK KEEP-ALIVE SERVER (Render Web Service အတွက်)
# ---------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "✨ Character Catch Auto Catcher Web Service is alive!"

@app.route('/health')
def health():
    return "OK", 200

def ping_self():
    """Render ၏ 15 မိနစ် Inactivity Sleep ကို ကာကွယ်ရန် Self-ping လုပ်ခြင်း"""
    time.sleep(10)
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        url = "https://beta-no7j.onrender.com"  # လိုအပ်ပါက ပြောင်းရန်
        logger.info(f"🔄 Using hardcoded URL: {url}")
    
    logger.info(f"🔄 Self-ping စတင်ပါပြီ။ URL: {url}")
    while True:
        try:
            time.sleep(300)  # ၅ မိနစ်လျှင် တစ်ကြိမ်
            response = requests.get(f"{url}/health", timeout=10)
            logger.info(f"🟢 Ping အောင်မြင်သည် - Status: {response.status_code}")
        except Exception as e:
            logger.error(f"🔴 Ping ပျက်ကွက်သည်: {e}")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ---------------------------------------------------------
# ၅၀ စက္ခတ်တစ်ကြိမ် Script ကို Restart ချမည့် System
# ---------------------------------------------------------
def auto_restart_system():
    """၅၀ စက္ခတ်ပြည့်တိုင်း Script တစ်ခုလုံးကို အလိုအလျောက် Restart ချပေးသည်"""
    while True:
        time.sleep(50)  # ၅၀ စက္ခတ် စောင့်မည်
        logger.info("🔄 ၅၀ စက္ခတ်ပြည့်သွားပြီဖြစ်ပါ၍ Script ကို Restart ချနေပါပြီ...")
        os._exit(0)  # Render Web Service က Script သေသွားတာနဲ့ အလိုအလျောက် ပြန်စ (Restart) ပေးပါလိမ့်မယ်

# ---------------------------------------------------------
# TELEGRAM EVENT HANDLERS (Auto Catcher & Forwarding)
# ---------------------------------------------------------

@client.on(events.NewMessage(incoming=True))
async def handle_incoming_messages(event):
    try:
        chat_id = event.chat_id
        
        # ၁။ သတ်မှတ်ထားသော Group ၃ ခုထဲကလာသော မက်ဆေ့ခ်ျများကို သင့်ထート (ADMIN_USER_ID) သို့ Forward မည်
        if chat_id in TARGET_CHATS:
            # မက်ဆေ့ခ်ျကို သင့်ထံ Forward မည် (Original Group ID ကို Reply ပြန်တဲ့အခါ သိနိုင်ရန် Caption သို့မဟုတ် Metadata တွင် သိမ်းဆည်းနိုင်သည်)
            forwarded_msg = await client.forward_messages(ADMIN_USER_ID, event.message)
            logger.info(f"📤 Group ({chat_id}) မှ မက်ဆေ့ခ်ျကို Admin ထံ Forward ပြီးပါပြီ။")

        # ၂။ သင်က (ADMIN_USER_ID) Forward လုပ်ထားတဲ့ မက်ဆေ့ခ်ျကို Reply ပြန်လာသည့်အခါ
        if event.is_reply and event.sender_id == ADMIN_USER_ID:
            reply_msg = await event.get_reply_message()
            if reply_msg:
                # Forward လုပ်ထားသော မက်ဆေ့ခ်ျ၏ မူရင်း Group ID ကို ရှာဖွေခြင်း
                original_chat_id = reply_msg.forward_from_chat.id if reply_msg.forward_from_chat else None
                
                # အကယ်၍ Forward ထားတဲ့ နေရာက Group မဟုတ်ဘဲ Chat မျိုးဆိုရင် reply_msg ထဲက ယူရပါမည်။ 
                # (သို့မဟုတ် Telethon ရဲ့ forward info မှတဆင့် မူရင်း chat_id ကို ရယူခြင်း)
                if not original_chat_id and hasattr(reply_msg, 'fwd_from') and reply_msg.fwd_from:
                    if hasattr(reply_msg.fwd_from, 'from_id'):
                        # chat_id ကို fwd_from ထဲမှ ဆွဲထုတ်ခြင်း
                        pass
                
                # တကယ်လို့ original_chat_id ကို တိုက်ရိုက်မရရင် TARGET_CHATS ထဲက ပထမဆုံး Group သို့မဟုတ် 
                # မက်ဆေ့ခ်ျထဲမှာပါတဲ့ Group ID ကို သုံးနိုင်ရန် အောက်ပါအတိုင်း စစ်ဆေးပါမည်။
                
                # သင်ပေးပို့လိုက်သော စာသား (ဥပမာ - /catch name သို့မဟုတ် /grab name)
                text_to_send = event.raw_text.strip()
                
                # အကယ်၍ Forward မက်ဆေ့ခ်ျထဲမှာ မူရင်း Chat ID ပါလာလျှင် အဲ့ဒီထဲကို ပို့မည်၊ မပါလျှင် TARGET_CHATS ထဲက ပထမဆုံး Group သို့ ပို့မည်
                target_group = reply_msg.forward_from_chat.id if (reply_msg and reply_msg.forward_from_chat) else TARGET_CHATS[0]
                
                if target_group in TARGET_CHATS:
                    await client.send_message(target_group, text_to_send)
                    logger.info(f"📥 Group ({target_group}) သို့ '{text_to_send}' ကို ပို့လိုက်ပါပြီ။")
                    await event.respond("✅ ပို့ပြီးပါပြီ။")
                
    except Exception as e:
        logger.error(f"❌ Error in handle_incoming_messages: {e}")

# ---------------------------------------------------------
# MAIN RUNNER
# ---------------------------------------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("✨ Character Catch Userbot စတင်နေပါပြီ (Web Service Mode)...")
    print("=" * 50)

    # 1. Flask server ကို Background thread တွင် Run မည်
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask server started")

    # 2. Self-ping ကို Background thread တွင် Run မည်
    ping_thread = threading.Thread(target=ping_self, daemon=True)
    ping_thread.start()
    print("✅ Self-ping system started")

    # 3. ၅၀ စက္ခတ်တစ်ကြိမ် Restart ချမည့် Thread ကို Run မည်
    restart_thread = threading.Thread(target=auto_restart_system, daemon=True)
    restart_thread.start()
    print("✅ 50-second Auto-Restart system started")

    print("=" * 50)
    print("🤖 Userbot is connecting to Telegram...")
    print("=" * 50)

    # Telethon Client ကို စတင်ခြင်း
    client.start()
    client.run_until_disconnected()

