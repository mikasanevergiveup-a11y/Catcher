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

# ၁။ Group ထဲတွင် ပုံ/ဖိုင် တွေ့သည်နှင့် အလိုအလျောက် Forward လုပ်မည်
@pyrogram_app.on_message((filters.photo | filters.document) & ~filters.chat(CHECKER_BOT_ID))
async def on_spawn_message(client, message):
    text = (message.caption or message.text or "").lower()
    group_name = message.chat.title or str(message.chat.id)
    
    target_checker_msg_id = None
    use_grab = "grab" in text or "husbando" in text or "waifu" in text or "new husbando" in text or "new waifu" in text

    try:
        fwd_msg = await message.forward(CHECKER_BOT_ID)
        target_checker_msg_id = fwd_msg.id
    except Exception:
        try:
            copy_msg = await message.copy(CHECKER_BOT_ID)
            target_checker_msg_id = copy_msg.id
        except Exception:
            pass

    if target_checker_msg_id:
        forwarded_messages[target_checker_msg_id] = (message.chat.id, use_grab)
        if len(forwarded_messages) > 100:
            oldest_key = list(forwarded_messages.keys())[0]
            del forwarded_messages[oldest_key]

# ၂။ အသုံးပြုသူကိုယ်တိုင် (Manual) Checker Bot ဆီ Forward လိုက်သောအခါတွင်လည်း မှတ်သားမည်
@pyrogram_app.on_message(filters.forwarded & filters.chat(CHECKER_BOT_ID))
async def on_manual_forward(client, message):
    # ကိုယ်တိုင် Forward လိုက်တဲ့ မက်ဆေ့ချ်က ဘယ် Group ကနေ ပါလာလဲဆိုတာကို ရှာမည်
    fwd_from = message.forward_from_chat
    if fwd_from:
        text = (message.caption or message.text or "").lower()
        use_grab = "grab" in text or "husbando" in text or "waifu" in text or "new husbando" in text or "new waifu" in text
        forwarded_messages[message.id] = (fwd_from.id, use_grab)
        print(f"📥 Manual Forward မိပါပြီ (Group ID: {fwd_from.id})")

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
        elif message.reply_to_message.forward_from_message_id:
            orig_id = message.reply_to_message.forward_from_message_id
            if orig_id in forwarded_messages:
                target_group, should_use_grab = forwarded_messages[orig_id]
                del forwarded_messages[orig_id]
    
    if not target_group and forwarded_messages:
        last_key = list(forwarded_messages.keys())[-1]
        target_group, should_use_grab = forwarded_messages[last_key]
        del forwarded_messages[last_key]

    match = re.search(r"((?:/catch|/grab|/check)\s+[^\n]+)", msg_text, re.IGNORECASE)
    
    if match:
        catch_cmd = match.group(1).strip()
        catch_cmd = re.sub(r"@[a-zA-Z0-9_]+bot", "", catch_cmd, flags=re.IGNORECASE).strip()

        if should_use_grab and catch_cmd.startswith("/catch"):
            catch_cmd = catch_cmd.replace("/catch", "/grab", 1)
        elif not should_use_grab and catch_cmd.startswith("/grab"):
            catch_cmd = catch_cmd.replace("/grab", "/catch", 1)
    else:
        match_alt = re.search(r"(?:Full|Name|Character|Hint)\s*[:\-]?\s*([^\n]+)", msg_text, re.IGNORECASE)
        if match_alt:
            val = match_alt.group(1).strip()
            val = re.sub(r"@[a-zA-Z0-9_]+bot", "", val, flags=re.IGNORECASE).strip()
            prefix = "/grab" if should_use_grab else "/catch"
            catch_cmd = val if val.startswith("/") else f"{prefix} {val}"
        else:
            clean_text = re.sub(r"@[a-zA-Z0-9_]+bot", "", msg_text, flags=re.IGNORECASE).strip()
            if clean_text.startswith(("/", "/grab", "/catch")):
                catch_cmd = clean_text
            else:
                catch_cmd = None

    if catch_cmd and target_group:
        try:
            await client.send_message(target_group, catch_cmd)
            print(f"🎯 Group ထဲသို့ အဖြေ ပို့ပြီးပါပြီ: {catch_cmd}")
        except Exception as e:
            print(f"❌ အဖြေပို့၍မရပါ: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    pyrogram_app.run()
    
