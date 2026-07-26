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
TARGET_GROUPS = [-1001947407820, -1003067509608, -1003854698282]

# Memory State 
last_active_group = None
last_use_grab = False
forwarded_records = {}

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

# ၁။ Group ထဲတွင် လှုပ်ရှားမှုရှိတိုင်း Group ID ကို အမြဲမှတ်ထားမည် (Hand/Manual အတွက် အရေးကြီးသည်)
@pyrogram_app.on_message(filters.chat(TARGET_GROUPS), group=-1)
async def track_groups(client, message):
    global last_active_group
    last_active_group = message.chat.id

# ၂။ Auto Spawn Detection (Group ထဲတွင် Spawn ပေါ်လာပါက Auto ပို့မည်)
@pyrogram_app.on_message(filters.chat(TARGET_GROUPS) & (filters.photo | filters.document), group=0)
async def auto_spawn_handler(client, message):
    global last_active_group, last_use_grab
    
    text = (message.caption or message.text or "").lower()
    if not text:
        return

    is_spawn = False
    use_grab = False
    
    if "waifu" in text or "husbando" in text or "grab" in text:
        is_spawn = True
        use_grab = True
    elif "spawned" in text or "catch" in text:
        is_spawn = True
        use_grab = False
        
    if not is_spawn:
        return
        
    last_active_group = message.chat.id
    last_use_grab = use_grab
    
    print(f"\n⚡ [Auto] Group ({message.chat.id}) တွင် Spawn တွေ့ရှိသည် Checker ဆီ ပို့နေပါပြီ...")
    
    try:
        fwd = await message.forward(CHECKER_BOT_ID)
        forwarded_records[fwd.id] = (message.chat.id, use_grab)
        print("✅ Auto-Forward အောင်မြင်သည်!")
    except Exception:
        try:
            cpy = await message.copy(CHECKER_BOT_ID)
            forwarded_records[cpy.id] = (message.chat.id, use_grab)
            print("✅ Auto-Copy အောင်မြင်သည်!")
        except Exception as e:
            print(f"❌ Auto ပို့၍မရပါ: {e}")

# ၃။ Manual / Hand Forward လုပ်သည့်အခါ (အစ်ကို ကိုယ်တိုင် Forward လိုက်လျှင် သိရှိရန်)
@pyrogram_app.on_message(filters.chat(CHECKER_BOT_ID) & filters.outgoing)
async def manual_forward_handler(client, message):
    global last_active_group, last_use_grab
    text = (message.caption or message.text or "").lower()
    
    if "waifu" in text or "husbando" in text or "grab" in text:
        last_use_grab = True
    elif "spawned" in text or "catch" in text:
        last_use_grab = False
        
    if message.forward_from_chat and message.forward_from_chat.id in TARGET_GROUPS:
        last_active_group = message.forward_from_chat.id
        
    forwarded_records[message.id] = (last_active_group, last_use_grab)
    print(f"📥 [Hand/Manual] Forward လုပ်တာကို မှတ်သားပြီးပါပြီ (Group: {last_active_group} | Grab: {last_use_grab})")

# ၄။ Checker Bot မှ အဖြေပြန်လာသောအခါ Auto & Hand နှစ်ခုစလုံးအတွက် Group ထဲသို့ အဖြေပို့မည်
@pyrogram_app.on_message(filters.chat(CHECKER_BOT_ID) & filters.incoming)
async def checker_reply_handler(client, message):
    global last_active_group, last_use_grab
    
    target_group = last_active_group
    use_grab = last_use_grab
    
    # Reply ပြန်လာသော မက်ဆေ့ချ် ID ကို စစ်ဆေးမည်
    if message.reply_to_message:
        rep_id = message.reply_to_message.id
        if rep_id in forwarded_records:
            target_group, use_grab = forwarded_records[rep_id]

    if not target_group:
        print("❌ ပစ်မှတ် Group ကို ရှာမတွေ့ပါ။")
        return

    text = message.text or message.caption or ""
    character_name = ""
    
    match_name = re.search(r"NAME\s*[:\-]?\s*([^|\n]+)", text, re.IGNORECASE)
    match_full = re.search(r"Full\s*[:\-]?\s*/(?:catch|grab)\s+([^\n]+)", text, re.IGNORECASE)
    match_cmd = re.search(r"/(?:catch|grab)\s+([^\n]+)", text, re.IGNORECASE)
    
    if match_name:
        character_name = match_name.group(1).strip()
    elif match_full:
        character_name = match_full.group(1).strip()
    elif match_cmd:
        character_name = match_cmd.group(1).strip()
        
    if character_name:
        character_name = re.sub(r"@[a-zA-Z0-9_]+bot", "", character_name, flags=re.IGNORECASE).strip()
        
        prefix = "/grab" if use_grab else "/catch"
        final_cmd = f"{prefix} {character_name}"
        
        try:
            await client.send_message(target_group, final_cmd)
            print(f"🎯 Group ({target_group}) သို့ အဖြေ ပို့ပြီးပါပြီ: {final_cmd}")
        except Exception as e:
            print(f"❌ အဖြေပို့၍မရပါ Error: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    pyrogram_app.run()

