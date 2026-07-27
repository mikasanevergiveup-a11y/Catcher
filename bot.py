import os
import time
import threading
import requests
import logging
import asyncio
from collections import OrderedDict
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import FloodWait

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

# Target Groups နှင့် Card Reader Bot ID
TARGET_CHATS = [-1004295330651, -1003315850707, -1003854698282]
CARD_READER_BOT_ID = 8506436817

# Forward လုပ်ခဲ့သည့် Message ID နှင့် Group ID များကို မှတ်သားရန်
forward_history = OrderedDict()
LAST_CHAT_ID = TARGET_CHATS[0]

# Pyrogram Client
app_client = Client(
    "character_catcher_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# ---------------------------------------------------------
# FLASK KEEP-ALIVE SERVER (Render အတွက်)
# ---------------------------------------------------------
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✨ Auto & Hand Character Catcher Bot is Active!"

@flask_app.route('/health')
def health():
    return "OK", 200

def ping_self():
    time.sleep(10)
    url = os.environ.get("RENDER_EXTERNAL_URL", "https://beta-no7j.onrender.com")
    while True:
        try:
            time.sleep(300)
            requests.get(f"{url}/health", timeout=10)
        except Exception:
            pass

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def auto_restart_system():
    while True:
        time.sleep(50)
        logger.info("🔄 ၅၀ စက္ခတ်ပြည့်၍ Restart ချနေပါသည်...")
        os._exit(0)

# =========================================================
# PYROGRAM EVENT HANDLERS
# =========================================================

# ---------------------------------------------------------
# ၁။ AUTO SYSTEM: Group (၃) ခုမှ Spawn မက်ဆေ့ခ်ျများကို Card Reader ဆီ Auto Forward မည်
# ---------------------------------------------------------
@app_client.on_message(filters.chat(TARGET_CHATS) & filters.incoming)
async def auto_forward_spawns(client, message):
    global LAST_CHAT_ID
    try:
        text = (message.caption or message.text or "").lower()
        
        # ပုံပါလာလျှင် သို့မဟုတ် Spawn စာသားပါလာလျှင် Auto Forward မည်
        is_spawn = any(kw in text for kw in [
            "spawn", "waifu", "husbando", "harem", "/catch", "/grab", "appeared"
        ]) or bool(message.photo)
        
        if is_spawn:
            chat_id = message.chat.id
            LAST_CHAT_ID = chat_id
            
            # Card Reader Bot ဆီသို့ Auto Forward မည်
            fwd_msg = await message.forward(CARD_READER_BOT_ID)
            if fwd_msg:
                forward_history[fwd_msg.id] = chat_id
                if len(forward_history) > 50:
                    forward_history.popitem(last=False)
                    
            logger.info(f"⚡ [AUTO] Group ({chat_id}) မှ Spawn ကို Card Reader ဆီ Auto Forward လိုက်ပါပြီ။")
            await asyncio.sleep(0.5)

    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f"❌ Auto Forward Error: {e}")

# ---------------------------------------------------------
# ၂။ HAND SYSTEM: မိမိကိုယ်တိုင် Hand ဖြင့် Forward လိုက်သော မက်ဆေ့ခ်ျကို မှတ်သားမည်
# ---------------------------------------------------------
@app_client.on_message(filters.me & filters.chat(CARD_READER_BOT_ID) & filters.forwarded)
async def hand_forward_tracker(client, message):
    global LAST_CHAT_ID
    try:
        if message.forward_from_chat and message.forward_from_chat.id in TARGET_CHATS:
            chat_id = message.forward_from_chat.id
            LAST_CHAT_ID = chat_id
            forward_history[message.id] = chat_id
            logger.info(f"🖐️ [HAND] မိမိကိုယ်တိုင် Group ({chat_id}) မှ Spawn ကို Forward လုပ်လိုက်သည်ကို မှတ်သားလိုက်ပါပြီ။")
    except Exception as e:
        logger.error(f"❌ Hand Forward Tracker Error: {e}")

# ---------------------------------------------------------
# ၃။ AUTO-SEND COMMAND: Card Reader မှ ပြန်လာသော /catch, /grab ကို Group ထဲ Auto ပြန်ပို့မည်
# ---------------------------------------------------------
@app_client.on_message(filters.chat(CARD_READER_BOT_ID) & filters.incoming)
async def process_card_reader_response(client, message):
    global LAST_CHAT_ID
    try:
        text = message.text or message.caption or ""
        
        if "/catch" in text.lower() or "/grab" in text.lower():
            target_chat = None
            
            # Reply မက်ဆေ့ခ်ျဖြစ်ပါက သက်ဆိုင်ရာ Group ကို ရှာမည်
            if message.reply_to_message and message.reply_to_message.id in forward_history:
                target_chat = forward_history[message.reply_to_message.id]
            
            # မတွေ့ပါက နောက်ဆုံး Forward လုပ်ခဲ့သော Group ID ကို ယူမည်
            if not target_chat:
                target_chat = LAST_CHAT_ID
                
            await client.send_message(target_chat, text)
            logger.info(f"🚀 [SENT] Group ({target_chat}) ထဲသို့ '{text}' ကို Auto ပို့လိုက်ပါပြီ။")
            
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f"❌ Process Response Error: {e}")

# =========================================================
# MAIN RUNNER
# =========================================================
if __name__ == "__main__":
    print("=" * 50)
    print("✨ Auto & Hand Character Catcher System Started!")
    print("=" * 50)

    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    threading.Thread(target=auto_restart_system, daemon=True).start()

    app_client.run()

