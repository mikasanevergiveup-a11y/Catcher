import os
import sys
import time
import threading
import requests
import logging
import asyncio
from flask import Flask
from pyrogram import Client, filters, idle
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
TARGET_CHATS = [-1001947407820, -1003854698282]
CARD_READER_BOT_ID = 8506436817

# နောက်ဆုံး Spawn ခဲ့သော Group ID ကို မှတ်သားရန်
LAST_CHAT_ID = TARGET_CHATS[0]

# Pyrogram Client
app_client = Client(
    "character_catcher_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# ---------------------------------------------------------
# FLASK KEEP-ALIVE SERVER & RESTART SYSTEM
# ---------------------------------------------------------
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✨ Character Catcher Bot is Active 24/7!"

@flask_app.route('/health')
def health():
    return "OK", 200

def ping_self():
    time.sleep(10)
    url = os.environ.get("RENDER_EXTERNAL_URL", "https://catcher-16m2.onrender.com")
    while True:
        try:
            time.sleep(300)
            requests.get(f"{url}/health", timeout=10)
        except Exception:
            pass

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# 🕒 ၃ မိနစ် (၁၈၀ စက္ခန့်) တစ်ခါ Auto Restart ချပေးမည့် Function
def auto_restart_system():
    time.sleep(180)
    logger.info("🔄 ၃ မိနစ်ပြည့်သွားပါပြီ။ Bot ကို Auto Restart ချနေပါသည်...")
    os.execv(sys.executable, ['python'] + sys.argv)

# =========================================================
# PYROGRAM EVENT HANDLERS
# =========================================================

# 🟢 [TEST COMMAND]
@app_client.on_message(filters.me & filters.command("ping", prefixes="."))
async def ping_command(client, message):
    await message.reply_text(f"🏓 **Pong! Bot is perfectly alive.**\n📁 ဒီ Group ရဲ့ ID မှာ: `{message.chat.id}` ဖြစ်ပါတယ်။")

# ၁။ AUTO SYSTEM (Group မှ Card Reader သို့ Auto Forward မည်)
@app_client.on_message(filters.chat(TARGET_CHATS) & filters.incoming)
async def auto_forward_spawns(client, message):
    global LAST_CHAT_ID
    try:
        text = str(message.caption or message.text or "").lower()
        
        spawn_keywords = [
            "a character has spawned", 
            "new waifu is here", 
            "new husbando is here",
            "grab using",
            "catch using"
        ]
        
        is_spawn = bool(message.photo) and any(kw in text for kw in spawn_keywords)
        
        if is_spawn:
            LAST_CHAT_ID = message.chat.id
            logger.info(f"⚡ [AUTO] Group ({LAST_CHAT_ID}) မှ Spawn အစစ် တွေ့ရှိပါသည်။ Card Reader ဆီသို့ Forward နေပါပြီ...")
            
            await client.forward_messages(
                chat_id=CARD_READER_BOT_ID,
                from_chat_id=message.chat.id,
                message_ids=message.id
            )
            
    except FloodWait as e:
        logger.warning(f"⚠️ Telegram မှ {e.value} စက္ကန့် စောင့်ခိုင်းထားပါသည်။")
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f"❌ Auto Forward Error: {e}")

# ၂. HAND SYSTEM (ကိုယ်တိုင် Forward လျှင် Group ID ကို ခြေရာခံမည်)
@app_client.on_message(filters.me & filters.chat(CARD_READER_BOT_ID))
async def hand_tracker(client, message):
    global LAST_CHAT_ID
    try:
        if message.forward_from_chat and message.forward_from_chat.id in TARGET_CHATS:
            LAST_CHAT_ID = message.forward_from_chat.id
            logger.info(f"🖐️ [HAND] သင်ကိုယ်တိုင် Group ({LAST_CHAT_ID}) မှ Forward လိုက်သည်ကို မှတ်သားထားပါပြီ။")
    except Exception as e:
        logger.error(f"❌ Hand Tracker Error: {e}")

# ၃။ COMMAND ပြန်လည်ပို့ခြင်း (Card Reader မှ Hint ကိုသာ ဖြတ်ထုတ်ပြီး Group ထဲ ပို့မည်)
@app_client.on_message(filters.chat(CARD_READER_BOT_ID) & filters.incoming)
async def send_command_to_group(client, message):
    global LAST_CHAT_ID
    try:
        text = str(message.text or message.caption or "")
        
        if text:
            final_text = text
            lines = text.split("\n")
            
            # "Hint :" ပါသော စာကြောင်းကိုသာ ရှာပြီး ဖြတ်ထုတ်မည်
            for line in lines:
                if "hint" in line.lower() and ("/" in line):
                    # ဥပမာ - "💎 Hint : /grab kaoru" ဆိုရင် သင်္ကေတနောက်ကဟာကို ယူမည်
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        final_text = parts[1].strip()
                        break
            
            logger.info(f"🤖 Card Reader မှ Hint ကို ဖြတ်ထုတ်ပြီးပါပြီ: {final_text}")
            await client.send_message(LAST_CHAT_ID, final_text)
            logger.info(f"🚀 [SUCCESS] Group ({LAST_CHAT_ID}) ထဲသို့ အောင်မြင်စွာ ပို့လိုက်ပါပြီ။")

    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f"❌ Command Send Error: {e}")

# =========================================================
# BOT STARTUP FUNCTION
# =========================================================
async def main():
    await app_client.start()
    logger.info("🔄 Group ID မှတ်ဉာဏ်များ (Cache) စတင်သွင်းယူနေပါသည်...")
    
    try:
        async for _ in app_client.get_dialogs(limit=200):
            pass
        logger.info("✅ Cache လုပ်ခြင်း ပြီးဆုံးပါပြီ။")
    except Exception as e:
        logger.warning(f"⚠️ Cache သွင်းယူရာတွင် Error: {e}")

    logger.info("🤖 Bot သည် အပြည့်အဝ အလုပ်လုပ်နေပါပြီ! Spawn များကို စောင့်ကြည့်နေပါသည်...")
    await idle()
    await app_client.stop()

# =========================================================
# MAIN RUNNER
# =========================================================
if __name__ == "__main__":
    print("=" * 50)
    print("✨ Character Catcher Bot Started Cleanly!")
    print("=" * 50)

    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    threading.Thread(target=auto_restart_system, daemon=True).start()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    
