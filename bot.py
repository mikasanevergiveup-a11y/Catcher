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

# သတ်မှတ်ထားသော Group 3 ခု
TARGET_CHATS = [-1004295330651, -1003315850707, -1003854698282]

# Card Reader Bot ရဲ့ User ID
CARD_READER_BOT_ID = 8506436817

# Group တစ်ခုချင်းစီက Spawn တဲ့ မက်ဆေ့ခ်ျတွေအတွက် မူရင်း Group ID ကို မှတ်သားရန် Dictionary
# Key: Forward လုပ်လိုက်တဲ့ Message ID, Value: မူရင်း Group Chat ID
message_origin_map = {}

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
        url = "https://beta-no7j.onrender.com"
    
    logger.info(f"🔄 Self-ping စတင်ပါပြီ။ URL: {url}")
    while True:
        try:
            time.sleep(300)
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
        time.sleep(50)  # ၅၀ စက္ခတ်ပြည့်တာနဲ့ Restart ချမည်
        logger.info("🔄 ၅၀ စက္ခတ်ပြည့်သွားပြီဖြစ်ပါ၍ Script ကို Restart ချနေပါပြီ...")
        os._exit(0)

# ---------------------------------------------------------
# PYROGRAM EVENT HANDLERS
# ---------------------------------------------------------

@app_client.on_message(filters.incoming)
async def handle_messages(client, message):
    try:
        chat_id = message.chat.id if message.chat else None
        
        # ၁။ Target Group 3 ခုထဲကလာတဲ့ Spawn မက်ဆေ့ခ်ျများကို Card Reader Bot ထံ Forward မည်
        if chat_id in TARGET_CHATS:
            text = message.caption or message.text or ""
            # Spawn ဖြစ်ကြောင်း သေချာစေရန် Keywords များကို စစ်ဆေးခြင်း
            if any(keyword in text.lower() for keyword in ["spawn", "appeared", "hurry-up", "catch", "grab"]):
                # Card Reader Bot ဆီသို့ Forward မည်
                forwarded_msg = await message.forward(CARD_READER_BOT_ID)
                
                # ဘယ် Group က လာတာလဲဆိုတာကို Message ID နဲ့ တွဲပြီး မှတ်ထားမည်
                if forwarded_msg:
                    message_origin_map[forwarded_msg.id] = chat_id
                
                logger.info(f"📤 Group ({chat_id}) မှ Spawn မက်ဆေ့ခ်ျကို Card Reader Bot ထံ Forward ပြီးပါပြီ။")

        # ၂။ Card Reader Bot (`CARD_READER_BOT_ID`) ဆီကနေ ပြန်လာတဲ့ စာကို စစ်ဆေးခြင်း
        if message.from_user and message.from_user.id == CARD_READER_BOT_ID:
            # Card Reader Bot က Reply ပြန်လာတာဖြစ်စေ၊ သို့မဟုတ် တိုက်ရိုက်ပို့တာဖြစ်စေ စစ်ဆေးမည်
            target_group = None
            
            # အကယ်၍ Card Reader Bot က Forward လုပ်ထားတဲ့ မက်ဆေ့ခ်ျ (သို့မဟုတ် Reply) ကို ပြန်ပို့တာဆိုရင်
            if message.reply_to_message:
                replied_id = message.reply_to_message.id
                if replied_id in message_origin_map:
                    target_group = message_origin_map[replied_id]
            
            # မူရင်း Group ID ကို ရှာမတွေ့ရင် မှတ်တမ်းထဲက နောက်ဆုံး Group (သို့မဟုတ် TARGET_CHATS ထဲက ပထမဆုံး Group) ကို သုံးမည်
            if not target_group and message_origin_map:
                target_group = list(message_origin_map.values())[-1]
            
            if not target_group:
                target_group = TARGET_CHATS[0]

            # Card Reader Bot ပို့လိုက်တဲ့ စာသား (ဥပမာ - /catch name သို့မဟုတ် /grab name)
            bot_text = message.text or message.caption or ""
            
            if bot_text and ("/catch" in bot_text or "/grab" in bot_text):
                await client.send_message(target_group, bot_text)
                logger.info(f"📥 Spawn ဖြစ်ခဲ့သော Group ({target_group}) ထဲသို့ '{bot_text}' ကို ပို့လိုက်ပါပြီ။")
                
    except Exception as e:
        logger.error(f"❌ Error in handle_messages: {e}")

# ---------------------------------------------------------
# MAIN RUNNER
# ---------------------------------------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("✨ Character Catcher Userbot စတင်နေပါပြီ...")
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

    app_client.run()
    
