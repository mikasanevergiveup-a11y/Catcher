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

# Spawn တောင်းဆိုထားသည့် Group ID များကို မှတ်ထားမည့် Queue
pending_groups = []

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
    # Chat ထဲသို့ Spawn/Character ရောက်လာပါက Checker Bot သို့ Forward လုပ်မည်
    if message.photo or "spawned" in text or "appeared" in text or "harem" in text:
        print(f"📥 Group [{message.chat.id}] တွင် Spawn တွေ့ပါသဖြင့် Checker သို့ Forward လုပ်နေသည်...")
        pending_groups.append(message.chat.id)
        try:
            await message.forward(CHECKER_BOT_ID)
        except Exception as e:
            print(f"❌ Forward Error: {e}")

@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    global pending_groups
    msg_text = message.text or message.caption or ""
    
    # "Full :" စာကြောင်းမှ /catch ... ကို ရှာဖွေခြင်း
    match = re.search(r"Full\s*:\s*(/catch\s+[^\n]+)", msg_text, re.IGNORECASE)
    
    if not match:
        match_alt = re.search(r"Full\s*:\s*([^\n]+)", msg_text, re.IGNORECASE)
        catch_cmd = f"/catch {match_alt.group(1).strip()}" if match_alt else None
    else:
        catch_cmd = match.group(1).strip()

    if catch_cmd and pending_groups:
        target_group = pending_groups.pop(0)
        print(f"📤 Group [{target_group}] သို့ ပို့လိုက်ပါပြီ: '{catch_cmd}'")
        try:
            await client.send_message(target_group, catch_cmd)
        except Exception as e:
            print(f"❌ Message send Error: {e}")

if __name__ == "__main__":
    # Flask Web Server Thread စတင်ခြင်း
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask Server စတင်လိုက်ပါပြီ။")

    # Self-ping Thread စတင်ခြင်း (50s တစ်ခါ)
    ping_thread = threading.Thread(target=ping_self, daemon=True)
    ping_thread.start()
    print("✅ 50s Self-ping စနစ် စတင်လိုက်ပါပြီ။")

    print("🤖 Userbot စတင် အလုပ်လုပ်နေပါပြီ...")
    pyrogram_app.run()
    
