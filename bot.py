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

# သတ်မှတ်ထားသော Group 3 ခု နှင့် Card Reader Bot ID
TARGET_CHATS = [-1004295330651, -1003315850707, -1003854698282]
CARD_READER_BOT_ID = 8506436817

# ---------------------------------------------------------
# MEMORY MANAGEMENT (To prevent memory leaks 24/7)
# ---------------------------------------------------------
class LimitedDict(OrderedDict):
    """Memory မပြည့်စေရန် နောက်ဆုံး Message ၂၀၀ ကိုသာ မှတ်ထားမည့် Dictionary"""
    def __init__(self, maxsize=200, *args, **kwds):
        self.maxsize = maxsize
        super().__init__(*args, **kwds)

    def __setitem__(self, key, value):
        if key not in self:
            if len(self) >= self.maxsize:
                self.popitem(last=False)
        super().__init__.__setitem__(key, value)

message_origin_map = LimitedDict(maxsize=200)

# ---------------------------------------------------------
# PYROGRAM CLIENT INITIALIZATION
# ---------------------------------------------------------
app_client = Client(
    "character_catcher_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# ---------------------------------------------------------
# FLASK KEEP-ALIVE SERVER
# ---------------------------------------------------------
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✨ Upgraded Character Catcher Bot is alive and running!"

@flask_app.route('/health')
def health():
    return "OK", 200

def ping_self():
    time.sleep(10)
    url = os.environ.get("RENDER_EXTERNAL_URL", "https://catcher-16m2.onrender.com")
    logger.info(f"🔄 Self-ping စတင်ပါပြီ။ URL: {url}")
    while True:
        try:
            time.sleep(300)
            response = requests.get(f"{url}/health", timeout=10)
        except Exception as e:
            pass

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def auto_restart_system():
    while True:
        time.sleep(50)
        logger.info("🔄 ၅၀ စက္ခတ်ပြည့်သွားပြီဖြစ်ပါ၍ Script ကို Restart ချနေပါပြီ...")
        os._exit(0)

# =========================================================
# PYROGRAM EVENT HANDLERS
# =========================================================

# ၁။ သတ်မှတ်ထားသော Group (၃) ခုမှ စာများကို ဖတ်ခြင်း (Read All Targeted)
@app_client.on_message(filters.chat(TARGET_CHATS) & filters.incoming)
async def group_message_handler(client, message):
    try:
        chat_id = message.chat.id
        text = message.caption or message.text or ""
        
        # Keyword ပါခြင်း (သို့မဟုတ်) ပုံ/ဖိုင် ပါခြင်းကို စစ်ဆေးမည်
        is_spawn_keyword = any(keyword in text.lower() for keyword in ["spawn", "appeared", "hurry-up", "catch", "grab"])
        has_media = bool(message.photo or message.document)
        
        # Spawn ဖြစ်နိုင်ချေရှိသမျှ အားလုံးကို ဖမ်းပြီး Forward မည်
        if is_spawn_keyword or has_media:
            forwarded_msg = await message.forward(CARD_READER_BOT_ID)
            
            if forwarded_msg:
                message_origin_map[forwarded_msg.id] = chat_id
            
            logger.info(f"📤 Group ({chat_id}) မှ မက်ဆေ့ခ်ျကို Card Reader Bot ထံ Forward ပြီးပါပြီ။")
            await asyncio.sleep(1)  # Spam မဖြစ်အောင် ၁ စက္ကန့် နားမည်

    except FloodWait as e:
        logger.warning(f"⚠️ Telegram Rate Limit! စက္ကန့် {e.value} ခန့် စောင့်ပါမည်။")
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f"❌ Error in group_message_handler: {e}")


# ၂။ Card Reader Bot ထံမှ စာပြန်လာပါက Auto System ဖြင့် မူရင်း Group သို့ ပြန်ပို့ခြင်း
@app_client.on_message(filters.chat(CARD_READER_BOT_ID) & filters.incoming)
async def auto_catch_handler(client, message):
    try:
        target_group = None
        
        if message.reply_to_message:
            replied_id = message.reply_to_message.id
            target_group = message_origin_map.get(replied_id)
        
        # မူရင်း Group မတွေ့ပါက နောက်ဆုံးဝင်ထားသည့် Group သို့ ပို့မည်
        if not target_group and message_origin_map:
            target_group = next(reversed(message_origin_map.values()))
        
        if not target_group:
            target_group = TARGET_CHATS[0]

        bot_text = message.text or message.caption or ""
        
        if bot_text and ("/catch" in bot_text or "/grab" in bot_text):
            await client.send_message(target_group, bot_text)
            logger.info(f"🚀 [AUTO] Group ({target_group}) ထဲသို့ '{bot_text}' ကို ပို့လိုက်ပါပြီ။")

    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f"❌ Error in auto_catch_handler: {e}")


# ၃။ Hand System (ကိုယ်တိုင် Card Reader ဆီမှ စာကို Reply ပြန်ခြင်း)
# filters.me ထည့်ထားသောကြောင့် မိမိကိုယ်တိုင် Reply ပြန်မှသာ အလုပ်လုပ်မည်ဖြစ်သည်
@app_client.on_message(filters.me & filters.chat(CARD_READER_BOT_ID) & filters.reply)
async def hand_catch_handler(client, message):
    try:
        replied_msg = message.reply_to_message
        
        if replied_msg and replied_msg.from_user and replied_msg.from_user.id == CARD_READER_BOT_ID:
            user_input = message.text.strip() if message.text else ""
            
            if user_input:
                replied_id = replied_msg.id
                target_group = message_origin_map.get(replied_id, TARGET_CHATS[0])
                
                # / (သို့) ! မပါဘဲ နာမည်သက်သက် ရိုက်ထည့်ပါက Auto ဖြည့်ပေးမည်
                if not user_input.startswith("/") and not user_input.startswith("!"):
                    original_text = replied_msg.caption or replied_msg.text or ""
                    if "grab" in original_text.lower():
                        final_command = f"/grab {user_input}"
                    else:
                        final_command = f"/catch {user_input}"
                else:
                    final_command = user_input

                await client.send_message(target_group, final_command)
                logger.info(f"✍️ [HAND] Group ({target_group}) ထဲသို့ '{final_command}' ကို ပို့လိုက်ပါပြီ။")
                
    except Exception as e:
        logger.error(f"❌ Error in hand_catch_handler: {e}")

# =========================================================
# MAIN RUNNER
# =========================================================
if __name__ == "__main__":
    print("=" * 50)
    print("✨ Upgraded Character Catcher Userbot စတင်နေပါပြီ...")
    print("=" * 50)

    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    threading.Thread(target=auto_restart_system, daemon=True).start()

    app_client.run()

