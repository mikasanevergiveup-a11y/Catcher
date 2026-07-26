import os
import time
import threading
import requests
import logging
from flask import Flask
from pyrogram import Client, filters

# ---------------------------------------------------------
# LOGGING CONFIGURATION
# ---------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# CONFIGURATIONS & ENVIRONMENT VARIABLES
# ---------------------------------------------------------
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

if not API_ID or not API_HASH or not SESSION_STRING:
    logger.error("❌ API_ID, API_HASH သို့မဟုတ် SESSION_STRING မတွေ့ရှိပါ။")
    exit(1)

API_ID = int(API_ID)

# သတ်မှတ်ထားသော Group 3 ခု (Integer ပုံစံဖြင့်)
TARGET_CHATS = [-1004295330651, -1003315850707, -1003854698282]

# သင့်ရဲ့ Telegram User ID (Forward လက်ခံမည့်သူ)
ADMIN_USER_ID = 8506436817

# Pyrogram Client ကို Session String ဖြင့် စတင်ခြင်း
app_client = Client(
    "character_catcher_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# ---------------------------------------------------------
# FLASK KEEP-ALIVE SERVER (Render Web Service အတွက်)
# ---------------------------------------------------------
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✨ Pyrogram Character Catcher Bot is alive and running!"

@flask_app.route('/health')
def health():
    return "OK", 200

def ping_self():
    """Render ၏ 15 မိနစ် Inactivity Sleep ကို ကာကွယ်ရန် Self-ping လုပ်ခြင်း"""
    time.sleep(10)
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        url = "https://beta-no7j.onrender.com"  # လိုအပ်ပါက ပြောင်းရန်
    
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
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ---------------------------------------------------------
# ၅၀ စက္ခတ်တစ်ကြိမ် Script ကို Restart ချမည့် System
# ---------------------------------------------------------
def auto_restart_system():
    while True:
        time.sleep(50)  # ၅၀ စက္ခတ် စောင့်မည်
        logger.info("🔄 ၅၀ စက္ခတ်ပြည့်သွားပြီဖြစ်ပါ၍ Script ကို Restart ချနေပါပြီ...")
        os._exit(0)

# ---------------------------------------------------------
# PYROGRAM EVENT HANDLERS (Forwarding & Catching)
# ---------------------------------------------------------

@app_client.on_message(filters.incoming)
async def handle_messages(client, message):
    try:
        chat_id = message.chat.id if message.chat else None
        
        # ၁။ သတ်မှတ်ထားသော Group 3 ခုထဲမှ မက်ဆေ့ခ်ျများကို Admin ထံ Forward မည်
        if chat_id in TARGET_CHATS:
            await message.forward(ADMIN_USER_ID)
            logger.info(f"📤 Group ({chat_id}) မှ မက်ဆေ့ခ်ျကို Admin ထံ Forward ပြီးပါပြီ။")

        # ၂။ Admin က Forward လုပ်ထားသော မက်ဆေ့ခ်ျကို Reply ပြန်လာသည့်အခါ
        if message.reply_to_message and message.from_user and message.from_user.id == ADMIN_USER_ID:
            reply_msg = message.reply_to_message
            
            # မူရင်း Group ID ကို Forward ထားသည့် Message မှ ရှာဖွေခြင်း
            original_chat_id = None
            if reply_msg.forward_from_chat:
                original_chat_id = reply_msg.forward_from_chat.id
            
            # အကယ်၍ မူရင်း Chat ID ရှာမတွေ့ပါက TARGET_CHATS ထဲမှ ပထမဆုံး Group သို့ ပို့မည်
            target_group = original_chat_id if original_chat_id in TARGET_CHATS else TARGET_CHATS[0]
            
            text_to_send = message.text.strip() if message.text else ""
            if text_to_send:
                await client.send_message(target_group, text_to_send)
                logger.info(f"📥 Group ({target_group}) သို့ '{text_to_send}' ကို ပို့လိုက်ပါပြီ။")
                await message.reply("✅ ပို့ပြီးပါပြီ။")
                
    except Exception as e:
        logger.error(f"❌ Error in handle_messages: {e}")

# ---------------------------------------------------------
# MAIN RUNNER
# ---------------------------------------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("✨ Pyrogram Character Catcher Userbot စတင်နေပါပြီ...")
    print("=" * 50)

    # 1. Flask server ကို Background thread တွင် Run မည်
    threading.Thread(target=run_flask, daemon=True).start()
    print("✅ Flask server started")

    # 2. Self-ping ကို Background thread တွင် Run မည်
    threading.Thread(target=ping_self, daemon=True).start()
    print("✅ Self-ping system started")

    # 3. ၅၀ စက္ခတ်တစ်ကြိမ် Restart ချမည့် Thread ကို Run မည်
    threading.Thread(target=auto_restart_system, daemon=True).start()
    print("✅ 50-second Auto-Restart system started")

    print("=" * 50)
    print("🤖 Pyrogram Client is starting...")
    print("=" * 50)

    # Pyrogram Client စတင်ခြင်း
    app_client.run()
    
