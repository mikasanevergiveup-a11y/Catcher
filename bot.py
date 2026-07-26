import os
import re
import threading
import time
import requests
from flask import Flask
from pyrogram import Client, filters, idle

API_ID = int(os.environ.get("API_ID", "38612444"))
API_HASH = os.environ.get("API_HASH", "49d750a1b3ae94cdec9a0df20535c3d9")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
CHECKER_BOT_ID = 8506436817

# နောက်ဆုံး Character Spawn ခဲ့သည့် Group ID ကို သိမ်းဆည်းရန်
last_spawned_chat_id = None

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
    time.sleep(15)
    while True:
        url = os.environ.get("RENDER_EXTERNAL_URL", "")
        if url:
            try:
                requests.get(f"{url}/health", timeout=10)
            except:
                pass
        time.sleep(50)

pyrogram_app = Client(
    "autocatch_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# 1. Group များကို စောင့်ကြည့်ပြီး Spawn တွေ့လျှင် Checker ထံ ပို့ရန်
@pyrogram_app.on_message()
async def on_spawn_message(client, message):
    try:
        if not message.chat:
            return
            
        chat_id = message.chat.id
        
        # Checker Bot ဆီကလာတာတွေနဲ့ ကိုယ့်အထွက် Message များကို ကျော်မည်
        if chat_id == CHECKER_BOT_ID or message.outgoing:
            return

        text = (message.text or message.caption or "").lower()
        
        # Character Spawn ဖြစ်ကြောင်းပြသော Keyword များ
        spawn_keywords = [
            "appeared", "spawned", "character", "harem", "guess", 
            "catch", "grab", "waifu", "husbando", "hurry"
        ]
        
        # ပုံပါရှိပြီး Spawn Keywords ထဲမှ တစ်ခုခုပါလျှင်
        if message.photo and any(kw in text for kw in spawn_keywords):
            global last_spawned_chat_id
            last_spawned_chat_id = chat_id
            print(f"🎯 Group [{chat_id}] တွင် Spawn တွေ့ပါပြီ! Checker သို့ Forward လုပ်နေသည်...")
            await message.forward(CHECKER_BOT_ID)
    except Exception as e:
        print(f"❌ Spawn Error: {e}")

# 2. Checker Bot ထံမှ အဖြေပြန်လာသောအခါ ဖြတ်ထုတ်ပြီး မူရင်း Group သို့ ပို့ရန်
@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    try:
        global last_spawned_chat_id
        msg_text = message.text or message.caption or ""
        print(f"📩 Checker Reply:\n{msg_text}")
        
        cmd_to_send = None
        
        # အဖြေထဲတွင် /catch, /grab, /guess စသည်တို့ပါက အပြည့်အစုံယူမည်
        match_cmd = re.search(r"((?:/catch|/grab|/guess|/hunt|/collect)\s+[^\n]+)", msg_text, re.IGNORECASE)
        if match_cmd:
            cmd_to_send = match_cmd.group(1).strip()
        else:
            # Full:, Name:, Hint: စသည်တို့နောက်မှ နာမည်ကို ဖြတ်ထုတ်မည်
            match_alt = re.search(r"(?:Full|Name|Character|Result|Hint)\s*[:\-]?\s*([^\n]+)", msg_text, re.IGNORECASE)
            if match_alt:
                raw_val = match_alt.group(1).strip()
                if raw_val.startswith("/") or raw_val.startswith("!"):
                    cmd_to_send = raw_val
                else:
                    text_lower = msg_text.lower()
                    if "grab" in text_lower:
                        prefix = "/grab"
                    elif "guess" in text_lower:
                        prefix = "/guess"
                    else:
                        prefix = "/catch"
                    cmd_to_send = f"{prefix} {raw_val}"
            else:
                clean_text = msg_text.strip()
                if clean_text:
                    if clean_text.startswith("/") or clean_text.startswith("!"):
                        cmd_to_send = clean_text
                    else:
                        cmd_to_send = f"/catch {clean_text}"

        # မူရင်း Group ထဲသို့ အဖြေ Command ပို့မည်
        if cmd_to_send and last_spawned_chat_id:
            target_group = last_spawned_chat_id
            print(f"📤 Group [{target_group}] သို့ ပို့မည်: '{cmd_to_send}'")
            await client.send_message(target_group, cmd_to_send)
            last_spawned_chat_id = None
        else:
            print("⚠️ ပို့ရန် Group ID မရှိပါ (သို့) Command မတွေ့ပါ။")
    except Exception as e:
        print(f"❌ Checker Reply Error: {e}")

def main():
    print("🤖 Pyrogram Userbot စတင် ချိတ်ဆက်နေပါပြီ...")
    try:
        pyrogram_app.start()
        print("✅ Userbot အောင်မြင်စွာ ချိတ်ဆက်ပြီးပါပြီ။")
    except Exception as e:
        print(f"❌ Userbot Start Error: {e}")
        return
    
    idle()
    pyrogram_app.stop()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    main()
    
