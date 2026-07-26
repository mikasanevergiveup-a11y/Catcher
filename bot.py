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

# စာလက်ခံမည့် Group ID (၃) ခု
SPAWN_GROUPS = [-1003854698282, -1001947407820, -1003067509608]

# Forward လုပ်ရမည့် Checker Bot ID
CHECKER_BOT_ID = 8506436817

# Forward လုပ်ထားသော မက်ဆေ့ခ်ျ ID နှင့် Group ID ကို မှတ်သားမည့် Dictionary
forwarded_messages = {}

# Flask App (Render Web Service အတွက်)
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Candy Hub Bot Alive!", 200

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
                res = requests.get(f"{url}/health", timeout=10)
                print(f"🟢 Self-ping successful! Status: {res.status_code}")
            except Exception as e:
                print(f"🔴 Self-ping error: {e}")
        else:
            print("⚠️ RENDER_EXTERNAL_URL env variable မရှိသေးပါ။")
        time.sleep(50)

# Pyrogram Client Setup
pyrogram_app = Client("autocatch_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

@pyrogram_app.on_message(filters.chat(SPAWN_GROUPS))
async def on_spawn_message(client, message):
    text = (message.text or message.caption or "").lower()
    
    # Spawn သို့မဟုတ် Waifu ပုံများ ဝင်လာခြင်းကို စစ်ဆေးမည်
    if message.photo and any(kw in text for kw in ["spawn", "appeared", "harem", "waifu", "grab", "catch"]):
        print(f"📥 Group [{message.chat.id}] တွင် Character တွေ့ပါသဖြင့် Checker သို့ Forward လုပ်နေသည်...")
        try:
            fwd_msg = await message.forward(CHECKER_BOT_ID)
            forwarded_messages[fwd_msg.id] = message.chat.id
        except Exception as e:
            print(f"❌ Forward Error: {e}")

@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    msg_text = message.text or message.caption or ""
    
    target_group = None
    if message.reply_to_message:
        target_group = forwarded_messages.get(message.reply_to_message.id)

    if not target_group and forwarded_messages:
        target_group = list(forwarded_messages.values())[-1]

    # Checker Bot မှ ပို့ပေးသော Full / catch / grab ကွန်မန်များကို ရှာဖွေခြင်း
    match = re.search(r"((?:/catch|/grab|/check)\s+[^\n]+)", msg_text, re.IGNORECASE)
    
    if match:
        catch_cmd = match.group(1).strip()
    else:
        match_alt = re.search(r"(?:Full|Name|Character)\s*[:\-]?\s*([^\n]+)", msg_text, re.IGNORECASE)
        if match_alt:
            val = match_alt.group(1).strip()
            catch_cmd = val if val.startswith("/") else f"/catch {val}"
        else:
            catch_cmd = msg_text.strip() if msg_text.strip().startswith("/") else None

    if catch_cmd and target_group:
        print(f"📤 Group [{target_group}] သို့ ပို့လိုက်ပါပြီ: '{catch_cmd}'")
        try:
            await client.send_message(target_group, catch_cmd)
            if message.reply_to_message and message.reply_to_message.id in forwarded_messages:
                del forwarded_messages[message.reply_to_message.id]
        except Exception as e:
            print(f"❌ Message send Error: {e}")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask Server စတင်လိုက်ပါပြီ။")

    ping_thread = threading.Thread(target=ping_self, daemon=True)
    ping_thread.start()
    print("✅ 50s Self-ping စနစ် စတင်လိုက်ပါပြီ။")

    print("🤖 Userbot စတင် အလုပ်လုပ်နေပါပြီ...")
    pyrogram_app.run()

