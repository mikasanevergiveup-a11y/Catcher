import os
import re
import threading
import time
import requests
from flask import Flask
from pyrogram import Client, filters

# Configuration from Environment Variables
API_ID = int(os.environ.get("API_ID", "38612444"))
API_HASH = os.environ.get("API_HASH", "49d750a1b3ae94cdec9a0df20535c3d9")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

# သတ်မှတ်ထားသော Group ID များ (လိုအပ်ပါက အခြား ID များကိုပါ ထည့်နိုင်သည်)
TARGET_GROUPS = [-1003067509608]

# Character Spawn တင်ပေးမည့် Bot ၃ ခု၏ ID များ
SPAWN_BOTS = [6157455819, 5934263177, 6212414747]

# Checker Bot ID
CHECKER_BOT_ID = 8506436817

# Request လာသည့် Group များကို မှတ်ထားမည့် Queue
pending_groups = []

# Flask App (Render Web Service အတွက်)
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is Alive!", 200

@app_flask.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def ping_self():
    """Render မအိပ်သွားစေရန် ၅၀ စက္ကန့်တစ်ခါ Self-ping လုပ်ပေးမည်"""
    time.sleep(10)
    while True:
        url = os.environ.get("RENDER_EXTERNAL_URL", "")
        if url:
            try:
                requests.get(f"{url}/health", timeout=10)
            except Exception:
                pass
        time.sleep(50)

# Pyrogram Client Setup
pyrogram_app = Client("autocatch_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

@pyrogram_app.on_message()
async def on_spawn_message(client, message):
    try:
        if not message.chat:
            return
        
        chat_id = message.chat.id
        if chat_id not in TARGET_GROUPS:
            return
        
        # သတ်မှတ်ထားသော Bot ၃ ခုထဲမှ တစ်ခုခု ပို့လိုက်သော မက်ဆေ့ဟုတ်လော စစ်ဆေးခြင်း
        if message.from_user and message.from_user.id in SPAWN_BOTS:
            print(f"📥 Group [{chat_id}] တွင် Bot [{message.from_user.id}] မှ Spawn ပို့လာသဖြင့် Checker သို့ Forward လုပ်နေသည်...")
            pending_groups.append(chat_id)
            await message.forward(CHECKER_BOT_ID)
    except Exception as e:
        # Peer id invalid သို့မဟုတ် မသိရသေးသော chat error များကို Bot မရပ်သွားစေရန် ကျော်လွှားမည်
        pass

@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    try:
        global pending_groups
        msg_text = message.text or message.caption or ""
        
        # Checker Bot မှ ပြန်လာသော စာသားမှ /check သို့မဟုတ် /catch ကို ရှာဖွေခြင်း
        match = re.search(r"(/check\s+[^\n]+|/catch\s+[^\n]+)", msg_text, re.IGNORECASE)
        if match:
            check_cmd = match.group(1).strip()
        else:
            match_alt = re.search(r"(?:Full|Result|Name)?\s*[:\-]?\s*([^\n]+)", msg_text, re.IGNORECASE)
            if match_alt:
                val = match_alt.group(1).strip()
                if not val.startswith("/"):
                    check_cmd = f"/check {val}"
                else:
                    check_cmd = val
            else:
                check_cmd = f"/check {msg_text.strip()}"

        if check_cmd and pending_groups:
            target_group = pending_groups.pop(0)
            print(f"📤 Group [{target_group}] သို့ ပို့လိုက်ပါပြီ: '{check_cmd}'")
            await client.send_message(target_group, check_cmd)
    except Exception as e:
        print(f"❌ Checker Reply Error: {e}")

if __name__ == "__main__":
    # Flask Web Server Thread စတင်ခြင်း
    threading.Thread(target=run_flask, daemon=True).start()

    # Self-ping Thread စတင်ခြင်း
    threading.Thread(target=ping_self, daemon=True).start()

    print("🤖 Userbot စတင် အလုပ်လုပ်နေပါပြီ...")
    pyrogram_app.run()
    
