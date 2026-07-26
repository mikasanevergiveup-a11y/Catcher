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
forwarded_mapping = {}  # Checker ဆီပို့လိုက်သော Message ID နှင့် မူလ Group ကို ချိတ်ဆက်ရန်
last_spawn_group = None # နောက်ဆုံး Spawn ပေါ်ခဲ့သော Group ID
last_spawn_grab = False # နောက်ဆုံး Spawn သည် Grab သုံးရန် လို/မလို

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

# ==========================================
# ၁။ Auto Spawn Detection (Group တိုင်းအတွက်)
# ==========================================
@pyrogram_app.on_message(filters.group)
async def on_group_message(client, message):
    global last_spawn_group, last_spawn_grab
    
    text = (message.caption or message.text or "").lower()
    if not text:
        return

    is_spawn = False
    use_grab = False

    # Spawn စာသားများကို အလွယ်တကူ ရှာဖွေခြင်း
    if "spawned" in text and "catch" in text:
        is_spawn = True
        use_grab = False
    elif "waifu" in text or "husbando" in text or "grab using" in text:
        is_spawn = True
        use_grab = True

    if not is_spawn:
        return

    # Spawn ပေါ်တာနဲ့ Group ID ကို အသေအချာ မှတ်ထားမည် (Manual Forward အတွက် Fallback)
    last_spawn_group = message.chat.id
    last_spawn_grab = use_grab
    print(f"\n⚡ [Group: {message.chat.title or message.chat.id}] တွင် Spawn အသစ်တွေ့ပါသည်!")

    # Auto Forward ကြိုးစားမည်
    try:
        fwd_msg = await message.forward(CHECKER_BOT_ID)
        forwarded_mapping[fwd_msg.id] = (message.chat.id, use_grab)
        print("✅ Auto-Forward အောင်မြင်ပါသည်။")
    except Exception as e:
        # Forward ပိတ်ထားလျှင် Copy ကူး၍ ပို့မည်
        try:
            copy_msg = await message.copy(CHECKER_BOT_ID)
            forwarded_mapping[copy_msg.id] = (message.chat.id, use_grab)
            print("✅ Auto-Copy အောင်မြင်ပါသည်။")
        except Exception as copy_e:
            print(f"❌ Auto ပို့၍မရပါ (Rare အတွက် ကိုယ်တိုင် Forward ပါ): {copy_e}")

    # Memory မပြည့်စေရန် ရှင်းလင်းခြင်း
    if len(forwarded_mapping) > 200:
        forwarded_mapping.pop(next(iter(forwarded_mapping)))


# ==========================================
# ၂။ Manual Forward (ကိုယ်တိုင် Forward လုပ်လျှင် အလုပ်လုပ်မည့် စနစ်)
# ==========================================
@pyrogram_app.on_message(filters.chat(CHECKER_BOT_ID) & filters.outgoing)
async def on_manual_forward(client, message):
    global last_spawn_group, last_spawn_grab
    
    text = (message.caption or message.text or "").lower()
    
    # Forward လိုက်သော စာသားကို ဖတ်ပြီး Grab/Catch ခွဲခြားမည်
    use_grab = last_spawn_grab
    if "waifu" in text or "husbando" in text or "grab" in text:
        use_grab = True
    elif "spawned" in text or "catch" in text:
        use_grab = False

    group_id = None
    
    # Original Group ID ကို ရနိုင်လျှင် ယူမည်၊ မရလျှင် နောက်ဆုံး Spawn ပေါ်ခဲ့သော Group ကို သုံးမည်
    if message.forward_from_chat:
        group_id = message.forward_from_chat.id
    else:
        group_id = last_spawn_group

    if group_id:
        forwarded_mapping[message.id] = (group_id, use_grab)
        print(f"📥 ကိုယ်တိုင် (Manual) Forward မိပါပြီ! (Group: {group_id} | Use Grab: {use_grab})")


# ==========================================
# ၃။ Checker Bot မှ အဖြေကို Group သို့ ပြန်ပို့ခြင်း
# ==========================================
@pyrogram_app.on_message(filters.chat(CHECKER_BOT_ID) & filters.incoming)
async def on_checker_reply(client, message):
    text = message.text or message.caption or ""
    
    target_group = None
    use_grab = False
    
    # Reply ပြန်လာသော မက်ဆေ့ချ် ID ကို အသုံးပြု၍ မူလ Group ကို ပြန်ရှာမည်
    if message.reply_to_message and message.reply_to_message.id in forwarded_mapping:
        target_group, use_grab = forwarded_mapping[message.reply_to_message.id]
    else:
        target_group = last_spawn_group
        use_grab = last_spawn_grab

    if not target_group:
        return

    character_name = ""
    
    # Checker Bot ၏ အဖြေမှ နာမည်ကို ထုတ်ယူခြင်း
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
        # Username များ ပါလာပါက ဖြတ်ထုတ်မည်
        character_name = re.sub(r"@[a-zA-Z0-9_]+bot", "", character_name, flags=re.IGNORECASE).strip()
        
        # Grab သို့မဟုတ် Catch ကို အတိအကျ သုံးမည်
        cmd_prefix = "/grab" if use_grab else "/catch"
        final_cmd = f"{cmd_prefix} {character_name}"

        try:
            await client.send_message(target_group, final_cmd)
            print(f"🎯 Group သို့ အဖြေ ပို့ပြီးပါပြီ: {final_cmd}")
        except Exception as e:
            print(f"❌ အဖြေပို့၍မရပါ: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    pyrogram_app.run()

