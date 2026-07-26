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

# သင်ပေးထားသော ID များကို တိကျစွာ သတ်မှတ်ထားခြင်း
CHECKER_BOT_ID = 8506436817
TARGET_GROUPS = [-1001947407820, -1003067509608, -1003854698282]
SPAWNER_BOTS = [6157455819, 5934263177, 6212414747]

forwarded_messages = {}
last_active_group = None
last_use_grab = False

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

# ၁။ သတ်မှတ်ထားသော Group ၃ ခုအတွင်းရှိ သတ်မှတ်ထားသော Spawner Bot ၃ ခုထံမှ စာများကိုသာ Auto ဖမ်းမည်
@pyrogram_app.on_message(filters.chat(TARGET_GROUPS))
async def on_spawn_message(client, message):
    global last_active_group, last_use_grab
    
    sender_id = message.from_user.id if message.from_user else None
    # Spawner Bot မှ လာသောစာ မဟုတ်ပါက ကျော်သွားမည်
    if sender_id not in SPAWNER_BOTS:
        return

    text = (message.caption or message.text or "").lower()
    group_name = message.chat.title or str(message.chat.id)
    
    # Grab သုံးရန် လိုမလို စစ်ဆေးမည်
    use_grab = "grab" in text or "husbando" in text or "waifu" in text or "new husbando" in text or "new waifu" in text
    
    last_active_group = message.chat.id
    last_use_grab = use_grab
    target_checker_msg_id = None

    print(f"\n⚡ [{group_name}] တွင် Card Spawner အသစ်တွေ့ရှိသည်၊ Card Reader ဆီသို့ ပို့နေပါပြီ...")

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

# ၂။ ကိုယ်တိုင် (Manual) Checker Bot ဆီသို့ Forward လုပ်သည့်အခါ (Grab/Catch အမှားပြဿနာ ဖြေရှင်းထားသည်)
@pyrogram_app.on_message(filters.chat(CHECKER_BOT_ID) & filters.forwarded)
async def on_manual_forward(client, message):
    global last_active_group, last_use_grab
    
    text = (message.caption or message.text or "").lower()
    use_grab = "grab" in text or "husbando" in text or "waifu" in text or "new husbando" in text or "new waifu" in text
    
    target_group = last_active_group
    # မူလ Group ကို ရှာနိုင်ပါက အစားထိုးမည်
    if message.forward_from_chat and message.forward_from_chat.id in TARGET_GROUPS:
        target_group = message.forward_from_chat.id

    if target_group:
        forwarded_messages[message.id] = (target_group, use_grab)
        last_use_grab = use_grab
        print(f"📥 Manual Forward မိပါပြီ (Grab အသုံးပြုရန်: {use_grab})")

# ၃။ Checker Bot မှ အဖြေပြန်လာသောအခါ Auto /grab သို့မဟုတ် /catch ဖြင့် Group သို့ ပြန်ပို့မည်
@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    global last_active_group, last_use_grab
    msg_text = message.text or message.caption or ""
    
    target_group = None
    should_use_grab = None
    
    # Message ID ချိတ်ဆက်မှု ရှာဖွေခြင်း
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
    
    # ID မတွေ့ပါက နောက်ဆုံး မှတ်ထားသော Group ကို သုံးမည်
    if not target_group:
        if forwarded_messages:
            last_key = list(forwarded_messages.keys())[-1]
            target_group, should_use_grab = forwarded_messages[last_key]
            del forwarded_messages[last_key]
        elif last_active_group:
            target_group = last_active_group
            should_use_grab = last_use_grab

    # Checker Bot ၏ အဖြေမှ Character Name ကိုသာ သီးသန့်ထုတ်ယူမည် (Checker Bot က ဘာပဲပြောပြော လျစ်လျူရှုမည်)
    character_name = ""
    match_name = re.search(r"NAME\s*[:\-]?\s*([^\n]+)", msg_text, re.IGNORECASE)
    
    if match_name:
        character_name = match_name.group(1).strip()
    else:
        match_full = re.search(r"Full\s*[:\-]?\s*/[a-zA-Z]+\s+([^\n]+)", msg_text, re.IGNORECASE)
        if match_full:
            character_name = match_full.group(1).strip()
        else:
            match_general = re.search(r"/(catch|grab|check)\s+([^\n]+)", msg_text, re.IGNORECASE)
            if match_general:
                character_name = match_general.group(2).strip()

    # Name ရလာပါက /grab သို့မဟုတ် /catch နှင့် တွဲ၍ ပို့မည်
    catch_cmd = None
    if character_name:
        # Username များ ပါလာပါက ဖြတ်ထုတ်မည်
        character_name = re.sub(r"@[a-zA-Z0-9_]+bot", "", character_name, flags=re.IGNORECASE).strip()
        
        # မူလ စာသားတွင် Grab သုံးရန် လိုအပ်ပါက /grab, မလိုအပ်ပါက /catch သုံးမည်
        prefix = "/grab" if should_use_grab else "/catch"
        catch_cmd = f"{prefix} {character_name}"

    if catch_cmd and target_group:
        try:
            await client.send_message(target_group, catch_cmd)
            print(f"🎯 Group ({target_group}) ထဲသို့ အဖြေ အောင်မြင်စွာ ပို့ပြီးပါပြီ: {catch_cmd}")
        except Exception as e:
            print(f"❌ အဖြေပို့၍မရပါ: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    pyrogram_app.run()

