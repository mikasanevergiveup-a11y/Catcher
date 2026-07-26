import os
import re
import threading
import time
import requests
from flask import Flask
from pyrogram import Client, filters

API_ID = int(os.environ.get("API_ID", "38612444"))
API_HASH = os.environ.get("API_HASH", "49d750a1b3ae94cdec9a0df20535c3d9")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

CHECKER_BOT_ID = 8506436817
forwarded_messages = {}
# နောက်ဆုံး Forward လုပ်ခဲ့သော Group ကို အမြဲမှတ်ထားမည့် Variable
last_target_group = None
last_group_name = "Unknown"

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
            except Exception:
                pass
        time.sleep(50)

pyrogram_app = Client("autocatch_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

@pyrogram_app.on_message(filters.photo & ~filters.chat(CHECKER_BOT_ID))
async def on_spawn_message(client, message):
    global last_target_group, last_group_name
    text = (message.caption or message.text or "").lower()
    group_name = message.chat.title or str(message.chat.id)
    
    print(f"👀 [Monitor] '{group_name}' တွင် ပုံတစ်ပုံ တွေ့ရှိပါသည်...")

    spawn_keywords = [
        "spawn", "appeared", "harem", "waifu", "husbando", 
        "grab", "catch", "character has spawned", "new waifu", "new husbando"
    ]
    
    is_spawn = any(kw in text for kw in spawn_keywords) or len(text) == 0

    if is_spawn:
        print(f"📌 [{group_name}] Spawn ပုံ အတည်ပြုပြီး Checker သို့ ပို့နေပါပြီ...")
        target_checker_msg = None
        try:
            fwd_msg = await message.forward(CHECKER_BOT_ID)
            target_checker_msg = fwd_msg.id
            print(f"✅ Forward အောင်မြင်သည် (ID: {target_checker_msg})")
        except Exception as e:
            print(f"⚠️ Forward Error ({e}) -> Copy ကူး၍ ပို့နေပါသည်...")
            try:
                copy_msg = await message.copy(CHECKER_BOT_ID)
                target_checker_msg = copy_msg.id
                print(f"✅ Copy ဖြင့် ပို့ခြင်း အောင်မြင်သည် (ID: {target_checker_msg})")
            except Exception as ex:
                print(f"❌ ပို့၍မရပါ: {ex}")

        if target_checker_msg:
            # မူလ Group ကို မှတ်သားမည်
            forwarded_messages[target_checker_msg] = (message.chat.id, group_name)
            last_target_group = message.chat.id
            last_group_name = group_name
            print(f"🎯 Last Target Group ကို အပ်ဒိတ်လုပ်ပြီးပါပြီ: {group_name}")

@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    global last_target_group, last_group_name
    msg_text = message.text or message.caption or ""
    print(f"📥 Checker Bot မှ စာလာပါပြီ: {msg_text}")
    
    target_group = None
    group_name = "Unknown Group"
    
    # 1. Reply လုပ်ထားခြင်း ရှိမရှိ စစ်မည်
    if message.reply_to_message:
        reply_id = message.reply_to_message.id
        if reply_id in forwarded_messages:
            target_group, group_name = forwarded_messages[reply_id]
            print(f"🎯 Reply မှတဆင့် Group တွေ့ရှိသည်: {group_name}")

    # 2. Reply မပါပါက (သို့မဟုတ်) ID မတွေ့ပါက နောက်ဆုံး Forward ခဲ့သော Group ကို သုံးမည်
    if not target_group and last_target_group:
        target_group = last_target_group
        group_name = last_group_name
        print(f"⚠️ Reply မရှိပါ၊ နောက်ဆုံး မှတ်ထားသော Group ကို သုံးပါမည်: {group_name}")

    # Command ဖမ်းယူခြင်း
    match = re.search(r"((?:/catch|/grab|/check)\s+[^\n]+)", msg_text, re.IGNORECASE)
    
    if match:
        catch_cmd = match.group(1).strip()
    else:
        match_alt = re.search(r"(?:Full|Name|Character|Hint)\s*[:\-]?\s*([^\n]+)", msg_text, re.IGNORECASE)
        if match_alt:
            val = match_alt.group(1).strip()
            catch_cmd = val if val.startswith("/") else f"/catch {val}"
        else:
            if msg_text.strip().startswith(("/", "/grab", "/catch")):
                catch_cmd = msg_text.strip()
            else:
                catch_cmd = None

    if catch_cmd and target_group:
        print(f"📤 [{group_name}] သို့ '{catch_cmd}' ကို ပို့နေပါပြီ...")
        try:
            await client.send_message(target_group, catch_cmd)
            print(f"🎉 အောင်မြင်စွာ ပို့ပြီးပါပြီ!")
            if message.reply_to_message and message.reply_to_message.id in forwarded_messages:
                del forwarded_messages[message.reply_to_message.id]
        except Exception as e:
            print(f"❌ ပို့၍မရပါ Error: {e}")
    else:
        print(f"❌ Command သို့မဟုတ် Target Group မရှိပါသဖြင့် ကျော်လိုက်ပါသည်။")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    print("🤖 Userbot စတင် အလုပ်လုပ်နေပါပြီ...")
    pyrogram_app.run()

