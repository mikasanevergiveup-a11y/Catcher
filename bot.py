import os
import re
import threading
import time
import requests
import asyncio
from flask import Flask
from pyrogram import Client, filters, idle

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
            
        # မိမိသတ်မှတ်ထားသော Group ၂ ခု မဟုတ်ပါက လျစ်လျူရှုမည် (Log တွင် အရှုပ်အရှင်းမဖြစ်စေရန်)
        if message.chat.id not in SPAWN_GROUPS:
            return
            
        text = (message.text or message.caption or "").lower()
        
        # Spawn မက်ဆေ့စ် ဟုတ်မဟုတ် စစ်ဆေးခြင်း
        is_spawn = (message.photo or "spawned" in text or "appeared" in text or "harem" in text or "character" in text)
        
        if is_spawn:
            print(f"✅ Group [ {message.chat.id} ] တွင် Spawn တွေ့ပါသဖြင့် Checker သို့ Forward လုပ်နေပါပြီ...")
            pending_groups.append(message.chat.id)
            await message.forward(CHECKER_BOT_ID)
            
    except Exception as e:
        # Error တက်ခဲ့လျှင် Bot ရပ်မသွားစေရန်
        pass

@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    try:
        global pending_groups
        msg_text = message.text or message.caption or ""
        print(f"📩 Checker မှ စာပြန်ရောက်လာပါသည်...")
        
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
            
    except Exception as e:
        print(f"❌ Group သို့ စာပြန်ပို့ရာတွင် Error ဖြစ်နေပါသည်: {e}")

async def main():
    await pyrogram_app.start()
    print("🔄 Userbot စတင်ပါပြီ။ မှတ်ဉာဏ် (Memory Cache) တည်ဆောက်နေပါသည်...")
    try:
        # Bot စတင်သည်နှင့် သင့်အကောင့်ရှိ Chat များကို ကြိုတင်ဖတ်မှတ်ထားမည် (Peer ID Error ဖြေရှင်းရန်)
        async for _ in pyrogram_app.get_dialogs(limit=200):
            pass
        print("✅ မှတ်ဉာဏ် တည်ဆောက်ပြီးပါပြီ။ Peer ID Error လုံးဝ မတက်နိုင်တော့ပါ။")
    except Exception as e:
        print(f"⚠️ မှတ်ဉာဏ် တည်ဆောက်ရာတွင် အခက်အခဲရှိပါသည်: {e}")

    print("🤖 Bot အပြည့်အဝ အလုပ်လုပ်နေပါပြီ (Spawn စောင့်နေပါသည်)...")
    await idle()
    await pyrogram_app.stop()

if __name__ == "__main__":
    # Flask နဲ့ Ping ကို သီးသန့် Run မည်
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    
    # Pyrogram Userbot ကို Event Loop ဖြင့် စတင်မည်
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
