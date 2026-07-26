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

pending_groups = []

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

@pyrogram_app.on_message()
async def on_spawn_message(client, message):
    try:
        if not message.chat:
            return
            
        chat_id = message.chat.id
        text = (message.text or message.caption or "").lower()
        
        # Bot အမျိုးအစားအမျိုးမျိုး၏ Spawn စာသားများကို စစ်ဆေးခြင်း
        spawn_keywords = [
            "appeared", "spawned", "character", "harem", "guess", 
            "catch", "grab", "waifu", "husbando", "hurry"
        ]
        
        if message.photo and any(kw in text for kw in spawn_keywords):
            print(f"🎯 Group [{chat_id}] တွင် Spawn တွေ့ပါပြီ! Checker သို့ Forward လုပ်နေသည်...")
            pending_groups.append(chat_id)
            try:
                await client.get_chat(chat_id)
            except:
                pass
            await message.forward(CHECKER_BOT_ID)
    except Exception as e:
        print(f"❌ Spawn Error: {e}")

@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    try:
        global pending_groups
        msg_text = message.text or message.caption or ""
        print(f"📩 Checker Reply:\n{msg_text}")
        
        cmd_to_send = None
        
        # 1. Checker မှ /catch, /guess, /grab စသည်တို့ တိုက်ရိုက်ပါလာပါက ယူမည်
        match_cmd = re.search(r"((?:/catch|/guess|/grab|/hunt|/collect)\s+[^\n]+)", msg_text, re.IGNORECASE)
        if match_cmd:
            cmd_to_send = match_cmd.group(1).strip()
        else:
            # 2. Full:, Name:, Hint: စသည့် စာသားများနောက်မှ အဖြေကို ဖြတ်ထုတ်မည်
            match_alt = re.search(r"(?:Full|Name|Character|Result|Hint)\s*[:\-]?\s*([^\n]+)", msg_text, re.IGNORECASE)
            if match_alt:
                raw_val = match_alt.group(1).strip()
                if raw_val.startswith("/") or raw_val.startswith("!"):
                    cmd_to_send = raw_val
                else:
                    # Bot ပုံစံပေါ်မူတည်၍ သင့်တော်သည့် command ကို သုံးမည်
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
                        cmd_to_send = f"/grab {clean_text}"

        if cmd_to_send and pending_groups:
            target_group = pending_groups.pop(0)
            print(f"📤 Group [{target_group}] သို့ ပို့မည်: '{cmd_to_send}'")
            await client.send_message(target_group, cmd_to_send)
    except Exception as e:
        print(f"❌ Checker Reply Error: {e}")

def main():
    print("🤖 Pyrogram Userbot စတင် ချိတ်ဆက်နေပါပြီ...")
    pyrogram_app.start()
    
    print("🔄 Group များနှင့် Chat များကို Cache လုပ်နေပါပြီ...")
    try:
        for dialog in pyrogram_app.get_dialogs():
            pass
        print("✅ Cache တည်ဆောက်ပြီးပါပြီ။ Bot အသင့်ဖြစ်ပါပြီ။")
    except Exception as e:
        print(f"⚠️ Cache Warning: {e}")
        
    idle()
    pyrogram_app.stop()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    main()

