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
last_active_group = None

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

# ၁။ Group ထဲမှ ပုံများကို အလိုအလျောက် Forward လုပ်မည်
@pyrogram_app.on_message((filters.photo | filters.document) & ~filters.chat(CHECKER_BOT_ID))
async def on_spawn_message(client, message):
    global last_active_group
    text = (message.caption or message.text or "").lower()
    group_name = message.chat.title or str(message.chat.id)
    last_active_group = message.chat.id
    
    use_grab = "grab" in text or "husbando" in text or "waifu" in text or "new husbando" in text or "new waifu" in text
    target_checker_msg_id = None

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

# ၂။ Manual Forward လုပ်သည့်အခါ
@pyrogram_app.on_message(filters.forwarded & filters.chat(CHECKER_BOT_ID))
async def on_manual_forward(client, message):
    global last_active_group
    fwd_from = message.forward_from_chat
    if fwd_from:
        text = (message.caption or message.text or "").lower()
        use_grab = "grab" in text or "husbando" in text or "waifu" in text or "new husbando" in text or "new waifu" in text
        forwarded_messages[message.id] = (fwd_from.id, use_grab)
        last_active_group = fwd_from.id
        print(f"📥 Manual Forward မိပါပြီ (Group ID: {fwd_from.id})")

# ၃။ Checker Bot မှ အဖြေပြန်လာသောအခါ
@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    global last_active_group
    msg_text = message.text or message.caption or ""
    target_group = None
    should_use_grab = False
    
    # Reply စစ်ဆေးခြင်း
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
    
    # အကယ်၍ မတွေ့ပါက နောက်ဆုံး မှတ်ထားသော Group ကို သုံးမည်
    if not target_group:
        if forwarded_messages:
            last_key = list(forwarded_messages.keys())[-1]
            target_group, should_use_grab = forwarded_messages[last_key]
            del forwarded_messages[last_key]
        elif last_active_group:
            target_group = last_active_group

    # အဖြေ Command ထုတ်ယူခြင်း (Full / Hint / catch / grab)
    catch_cmd = None
    
    # ပုံစံ ၁ - Full / Hint ပါသော စာသားများကို ရှာမည်
    match_full = re.search(r"Full\s*[:\-]?\s*(/[a-zA-Z]+\s+[^\n]+)", msg_text, re.IGNORECASE)
    match_hint = re.search(r"Hint\s*[:\-]?\s*(/[a-zA-Z]+\s+[^\n]+)", msg_text, re.IGNORECASE)
    match_general = re.search(r"((?:/catch|/grab|/check)\s+[^\n]+)", msg_text, re.IGNORECASE)
    match_name = re.search(r"NAME\s*[:\-]?\s*([^\n]+)", msg_text, re.IGNORECASE)

    if match_full:
        catch_cmd = match_full.group(1).strip()
    elif match_hint:
        catch_cmd = match_hint.group(1).strip()
    elif match_general:
        catch_cmd = match_general.group(1).strip()
    elif match_name:
        val = match_name.group(1).strip()
        prefix = "/grab" if should_use_grab else "/catch"
        catch_cmd = f"{prefix} {val}"

    if catch_cmd:
        catch_cmd = re.sub(r"@[a-zA-Z0-9_]+bot", "", catch_cmd, flags=re.IGNORECASE).strip()
        if should_use_grab and catch_cmd.startswith("/catch"):
            catch_cmd = catch_cmd.replace("/catch", "/grab", 1)
        elif not should_use_grab and catch_cmd.startswith("/grab"):
            catch_cmd = catch_cmd.replace("/grab", "/catch", 1)
    else:
        clean_text = re.sub(r"@[a-zA-Z0-9_]+bot", "", msg_text, flags=re.IGNORECASE).strip()
        if clean_text.startswith(("/", "/grab", "/catch")):
            catch_cmd = clean_text

    if catch_cmd and target_group:
        try:
            await client.send_message(target_group, catch_cmd)
            print(f"🎯 Group ထဲသို့ အဖြေ အောင်မြင်စွာ ပို့ပြီးပါပြီ: {catch_cmd}")
        except Exception as e:
            print(f"❌ အဖြေပို့၍မရပါ: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    pyrogram_app.run()

