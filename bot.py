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

# Group ထဲတွင် ပုံ (သို့) ဖိုင် တွေ့သည်နှင့် Forward ကို လုံးဝမသုံးဘဲ တိုက်ရိုက် Upload တင်မည် (Instant Speed)
@pyrogram_app.on_message((filters.photo | filters.document) & ~filters.chat(CHECKER_BOT_ID))
async def on_spawn_message(client, message):
    text = (message.caption or message.text or "").lower()
    group_name = message.chat.title or str(message.chat.id)
    
    print(f"\n⚡ [{group_name}] တွင် ပုံအသစ်တွေ့ရှိသည်၊ Checker ဆီသို့ အမြန်ဆုံး တင်နေပါပြီ...")
    
    target_checker_msg_id = None
    use_grab = "grab" in text or "husbando" in text or "waifu" in text or "new husbando" in text or "new waifu" in text

    try:
        # ပုံကို အမြန်ဆုံး ဒေါင်းလုဒ်ဆွဲမည်
        file_path = await message.download()
        if message.photo:
            sent_msg = await client.send_photo(CHECKER_BOT_ID, photo=file_path, caption=message.caption or "")
        else:
            sent_msg = await client.send_document(CHECKER_BOT_ID, document=file_path, caption=message.caption or "")
        
        target_checker_msg_id = sent_msg.id
        
        # ယာယီဖိုင်ကို ချက်ချင်းဖျက်မည်
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            
        print("🚀 Checker Bot ဆီသို့ ပုံရောက်ရှိသွားပါပြီ!")
    except Exception as e:
        print(f"❌ ပို့၍မရပါ Error: {e}")

    if target_checker_msg_id:
        forwarded_messages[target_checker_msg_id] = (message.chat.id, use_grab)
        if len(forwarded_messages) > 100:
            oldest_key = list(forwarded_messages.keys())[0]
            del forwarded_messages[oldest_key]

@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    msg_text = message.text or message.caption or ""
    target_group = None
    should_use_grab = False
    
    if message.reply_to_message:
        reply_id = message.reply_to_message.id
        if reply_id in forwarded_messages:
            target_group, should_use_grab = forwarded_messages[reply_id]
            del forwarded_messages[reply_id]
    
    if not target_group and forwarded_messages:
        last_key = list(forwarded_messages.keys())[-1]
        target_group, should_use_grab = forwarded_messages[last_key]
        del forwarded_messages[last_key]

    match = re.search(r"((?:/catch|/grab|/check)\s+[^\n]+)", msg_text, re.IGNORECASE)
    
    if match:
        catch_cmd = match.group(1).strip()
        if should_use_grab and catch_cmd.startswith("/catch"):
            catch_cmd = catch_cmd.replace("/catch", "/grab", 1)
        elif not should_use_grab and catch_cmd.startswith("/grab"):
            catch_cmd = catch_cmd.replace("/grab", "/catch", 1)
    else:
        match_alt = re.search(r"(?:Full|Name|Character|Hint)\s*[:\-]?\s*([^\n]+)", msg_text, re.IGNORECASE)
        if match_alt:
            val = match_alt.group(1).strip()
            prefix = "/grab" if should_use_grab else "/catch"
            catch_cmd = val if val.startswith("/") else f"{prefix} {val}"
        else:
            if msg_text.strip().startswith(("/", "/grab", "/catch")):
                catch_cmd = msg_text.strip()
            else:
                catch_cmd = None

    if catch_cmd and target_group:
        try:
            # အချိန်ဆိုင်းငံ့ခြင်းမရှိဘဲ ချက်ချင်း ပစ်လွှတ်ရန်
            await client.send_message(target_group, catch_cmd)
            print(f"🎯 Group ထဲသို့ အဖြေ အမြန်ဆုံး ပို့ပြီးပါပြီ: {catch_cmd}")
        except Exception as e:
            print(f"❌ အဖြေပို့၍မရပါ: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    pyrogram_app.run()

