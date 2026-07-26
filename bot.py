import os
import re
import threading
import time
import requests
import asyncio
from flask import Flask
from pyrogram import Client, filters, idle

API_ID = int(os.environ.get("API_ID", "38612444"))
API_HASH = os.environ.get("API_HASH", "49d750a1b3ae94cdec9a0df20535c3d9")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

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
            
        chat_id = message.chat.id
        text = (message.text or message.caption or "").lower()
        
        # ဓာတ်ပုံပါပြီး Spawn စာသားပါလာလျှင် Group ID မလိုဘဲ အလိုအလျောက် Forward မည်
        if message.photo and ("spawned" in text or "character" in text or "harem" in text):
            print(f"🎯 Group [ {chat_id} ] တွင် Spawn တွေ့ရှိပါသည်! Checker သို့ Forward လုပ်နေသည်...")
            pending_groups.append(chat_id)
            await message.forward(CHECKER_BOT_ID)
            
    except Exception as e:
        print(f"❌ Forward Error: {e}")

@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    try:
        global pending_groups
        msg_text = message.text or message.caption or ""
        print(f"📩 Checker မှ ပြန်လာသောစာသား:\n{msg_text}")
        
        catch_cmd = None
        match_catch = re.search(r"(/catch\s+[^\n]+|/check\s+[^\n]+)", msg_text, re.IGNORECASE)
        if match_catch:
            catch_cmd = match_catch.group(1).strip()
        else:
            match_alt = re.search(r"(?:Full|Name|Character|Result)\s*[:\-]?\s*([^\n]+)", msg_text, re.IGNORECASE)
            if match_alt:
                name = match_alt.group(1).strip()
                catch_cmd = f"/catch {name}" if not name.startswith("/") else name

        if catch_cmd and pending_groups:
            target_group = pending_groups.pop(0)
            print(f"📤 Group [{target_group}] သို့ ပို့လိုက်ပါပြီ: '{catch_cmd}'")
            await client.send_message(target_group, catch_cmd)
            
    except Exception as e:
        print(f"❌ Checker Reply Error: {e}")

async def main():
    await pyrogram_app.start()
    print("🔄 Userbot စတင်နေပါပြီ...")
    try:
        async for _ in pyrogram_app.get_dialogs(limit=100):
            pass
        print("✅ Cache တည်ဆောက်ပြီးပါပြီ။")
    except:
        pass

    print("🤖 Bot အသင့်ဖြစ်နေပါပြီ။ Group ထဲ Spawn စောင့်နေသည်...")
    await idle()
    await pyrogram_app.stop()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

