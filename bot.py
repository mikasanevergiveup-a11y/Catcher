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

# သင်ပေးထားသော Group ID (၂) ခု
SPAWN_GROUPS = [-1001947407820, -1003067509608]

# Forward လုပ်ရမည့် Checker Bot ID
CHECKER_BOT_ID = 8506436817

pending_groups = []

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
    time.sleep(10)
    while True:
        url = os.environ.get("RENDER_EXTERNAL_URL", "")
        if url:
            try:
                requests.get(f"{url}/health", timeout=10)
            except:
                pass
        time.sleep(50)

pyrogram_app = Client("autocatch_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

@pyrogram_app.on_message()
async def on_spawn_message(client, message):
    try:
        if not message.chat:
            return
            
        text = (message.text or message.caption or "").lower()
        
        # Spawn မက်ဆေ့စ် ဟုတ်မဟုတ် စစ်ဆေးခြင်း
        is_spawn = (message.photo or "spawned" in text or "appeared" in text or "harem" in text or "character" in text)
        
        if is_spawn:
            print(f"👀 သတိပြုရန်: Group ID [ {message.chat.id} ] တွင် Spawn မက်ဆေ့စ် တွေ့ပါသည်။")
            
            if message.chat.id not in SPAWN_GROUPS:
                print(f"🚫 ကျော်သွားပါမည်: ထို Group ID [ {message.chat.id} ] သည် သင်ထည့်ထားသော စာရင်းထဲတွင် မပါပါ။")
                return
                
            print(f"✅ မှန်ကန်သော Group [ {message.chat.id} ] ဖြစ်သဖြင့် Checker သို့ Forward လုပ်နေပါပြီ...")
            pending_groups.append(message.chat.id)
            await message.forward(CHECKER_BOT_ID)
            
    except Exception as e:
        print(f"❌ Spawn ဖမ်းယူရာတွင် Error ဖြစ်နေပါသည်: {e}")

@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    try:
        global pending_groups
        msg_text = message.text or message.caption or ""
        print(f"📩 Checker Bot ထံမှ စာပြန်ရောက်လာပါသည်: {msg_text[:30]}...")
        
        match = re.search(r"Full\s*:\s*(/catch\s+[^\n]+)", msg_text, re.IGNORECASE)
        
        if not match:
            match_alt = re.search(r"Full\s*:\s*([^\n]+)", msg_text, re.IGNORECASE)
            catch_cmd = f"/catch {match_alt.group(1).strip()}" if match_alt else None
        else:
            catch_cmd = match.group(1).strip()

        if catch_cmd and pending_groups:
            target_group = pending_groups.pop(0)
            print(f"📤 Group [{target_group}] သို့ ပို့လိုက်ပါပြီ: '{catch_cmd}'")
            await client.send_message(target_group, catch_cmd)
        else:
            print("⚠️ ပို့ရန် Group မရှိတော့ပါ သို့မဟုတ် Command ရှာမတွေ့ပါ။")
            
    except Exception as e:
        print(f"❌ Group သို့ စာပြန်ပို့ရာတွင် Error ဖြစ်နေပါသည်: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    print("🤖 Userbot စတင် အလုပ်လုပ်နေပါပြီ (Logs များကို စောင့်ကြည့်ပါ)...")
    pyrogram_app.run()
    
