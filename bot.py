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

# မှတ်ဉာဏ်စနစ်များ (Memory)
forwarded_mapping = {}  # Checker Message ID ကို မူလ Group နှင့် ချိတ်ဆက်ရန်
spawn_memory = {}       # Manual Forward လုပ်လျှင် ရှာနိုင်ရန် စာသားများကို မှတ်သားရန်
last_group = None
last_grab = False

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

# ၁။ Group အားလုံးမှ Spawn စာသားများကို အလိုအလျောက် ရှာဖွေဖမ်းယူမည် (ID အသေမသတ်မှတ်တော့ပါ)
@pyrogram_app.on_message(filters.group & (filters.photo | filters.document))
async def on_spawn_message(client, message):
    global last_group, last_grab
    
    caption = (message.caption or message.text or "").lower()
    is_spawn = False
    use_grab = False

    # ပုံ ၃ ပုံအရ စာသားများကို အတိအကျ စစ်ဆေးခြင်း
    if "spawned in the chat" in caption:
        is_spawn = True
        use_grab = False  # /catch ကို သုံးမည်
    elif "new waifu is here" in caption or "new husbando is here" in caption or "grab using" in caption:
        is_spawn = True
        use_grab = True   # /grab ကို သုံးမည်

    if not is_spawn:
        return  # Spawn မဟုတ်ပါက ကျော်သွားမည်

    group_id = message.chat.id
    last_group = group_id
    last_grab = use_grab

    # Manual Forward လုပ်လာပါက Group အတိအကျ ပြန်ရှာနိုင်ရန် Caption ကို မှတ်ထားမည်
    snippet = caption.replace('\n', ' ')[:60].strip()
    if snippet:
        spawn_memory[snippet] = (group_id, use_grab)

    print(f"\n⚡ [Group: {message.chat.title or group_id}] တွင် Spawn အသစ်တွေ့ပါသည်! Auto ပို့နေပါပြီ...")

    try:
        fwd_msg = await message.forward(CHECKER_BOT_ID)
        forwarded_mapping[fwd_msg.id] = (group_id, use_grab)
        print("✅ Auto-Forward အောင်မြင်ပါသည်။")
    except Exception as e:
        print(f"❌ Auto-Forward မအောင်မြင်ပါ: {e}")

    # Memory မပြည့်စေရန် အဟောင်းများကို ရှင်းလင်းမည်
    if len(forwarded_mapping) > 200:
        forwarded_mapping.pop(next(iter(forwarded_mapping)))
    if len(spawn_memory) > 200:
        spawn_memory.pop(next(iter(spawn_memory)))


# ၂။ ကိုယ်တိုင် (Manual) Forward လုပ်သည့်အခါ မူလ Group ကို အတိအကျ ပြန်ရှာမည်
@pyrogram_app.on_message(filters.chat(CHECKER_BOT_ID) & filters.outgoing)
async def on_manual_forward(client, message):
    global last_group, last_grab
    
    caption = (message.caption or message.text or "").lower()
    snippet = caption.replace('\n', ' ')[:60].strip()
    
    group_id = None
    use_grab = "grab" in caption or "waifu" in caption or "husbando" in caption

    # Forward လုပ်လာတဲ့ စာကို မှတ်ဉာဏ်ထဲမှာ ပြန်ရှာမည်
    if snippet in spawn_memory:
        group_id, mem_grab = spawn_memory[snippet]
        use_grab = use_grab or mem_grab
    elif message.forward_from_chat:
        group_id = message.forward_from_chat.id
    
    if group_id:
        forwarded_mapping[message.id] = (group_id, use_grab)
        last_group = group_id
        last_grab = use_grab
        print(f"📥 Manual Forward မိပါပြီ! (Group အမှန်: {group_id} | Use Grab: {use_grab})")


# ၃။ Checker Bot မှ အဖြေပြန်လာသောအခါ မှန်ကန်သော Group ထဲသို့ ပြန်ပို့မည်
@pyrogram_app.on_message(filters.chat(CHECKER_BOT_ID) & filters.incoming)
async def on_checker_reply(client, message):
    text = message.text or message.caption or ""
    
    target_group = None
    use_grab = False
    
    # Message ID ချိတ်ဆက်မှုကို အရင်ရှာမည်
    if message.reply_to_message and message.reply_to_message.id in forwarded_mapping:
        target_group, use_grab = forwarded_mapping[message.reply_to_message.id]
    else:
        # မတွေ့ပါက နောက်ဆုံး မှတ်ထားသော Group ကို သုံးမည်
        target_group = last_group
        use_grab = last_grab

    if not target_group:
        return

    character_name = ""
    
    # ဓာတ်ပုံထဲကအတိုင်း Checker Bot ၏ အဖြေ (NAME: Hinatsuru | 🆔 3143) ကို ဖမ်းယူခြင်း
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
        
        # Grab သို့မဟုတ် Catch ကို မှန်ကန်စွာ ရွေးချယ်မည်
        cmd_prefix = "/grab" if use_grab else "/catch"
        final_cmd = f"{cmd_prefix} {character_name}"

        try:
            await client.send_message(target_group, final_cmd)
            print(f"🎯 Group ({target_group}) သို့ အဖြေ မှန်ကန်စွာ ပို့ပြီးပါပြီ: {final_cmd}")
        except Exception as e:
            print(f"❌ အဖြေပို့၍မရပါ: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    pyrogram_app.run()

