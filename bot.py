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

# Memory Caches (Group တိုင်းအတွက် အလိုအလျောက် မှတ်သားမည့်နေရာ)
active_mapping = {}      # Checker Message ID နဲ့ Group ကို ချိတ်ဆက်ရန်
text_to_group = {}       # Manual Forward အတွက် စာသားနဲ့ Group ကို ချိတ်ဆက်ရန်
text_to_grab = {}        # Grab လား Catch လား ခွဲခြားရန်

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
# ၁။ Automatic System (Account joinထားသည့် Group တိုင်းတွင် အလုပ်လုပ်မည်)
# ==========================================
@pyrogram_app.on_message(filters.group & (filters.photo | filters.document))
async def auto_spawn_listener(client, message):
    text = (message.caption or message.text or "").lower()
    if not text:
        return

    # Spawn စာသား ဟုတ်မဟုတ် စစ်ဆေးခြင်း
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

    group_id = message.chat.id
    snippet = text.replace('\n', ' ')[:50].strip()

    # Manual Forward အတွက်ပါ တစ်ခါတည်း မှတ်ထားမည်
    text_to_group[snippet] = group_id
    text_to_grab[snippet] = use_grab

    print(f"\n⚡ [Auto] Group ({message.chat.title or group_id}) တွင် Spawn တွေ့ရှိသည် Checker ဆီ ပို့နေပါပြီ...")

    target_checker_msg_id = None
    try:
        fwd = await message.forward(CHECKER_BOT_ID)
        target_checker_msg_id = fwd.id
        print("✅ Auto-Forward အောင်မြင်သည်!")
    except Exception:
        try:
            cpy = await message.copy(CHECKER_BOT_ID)
            target_checker_msg_id = cpy.id
            print("✅ Auto-Copy အောင်မြင်သည်!")
        except Exception as e:
            print(f"❌ Auto ပို့၍မရပါ (Hand စနစ်ဖြင့် Forward နိုင်သည်): {e}")

    if target_checker_msg_id:
        active_mapping[target_checker_msg_id] = (group_id, use_grab)

    # Memory မပြည့်စေရန် ရှင်းလင်းခြင်း
    if len(active_mapping) > 200:
        active_mapping.pop(next(iter(active_mapping)))
    if len(text_to_group) > 200:
        text_to_group.pop(next(iter(text_to_group)))


# ==========================================
# ၂. Manual / Hand System (အစ်ကို ကိုယ်တိုင် Forward လုပ်သည့်အခါ)
# ==========================================
@pyrogram_app.on_message(filters.chat(CHECKER_BOT_ID) & filters.outgoing)
async def manual_forward_listener(client, message):
    text = (message.caption or message.text or "").lower()
    snippet = text.replace('\n', ' ')[:50].strip()

    target_group = None
    use_grab = "waifu" in text or "husbando" in text or "grab" in text

    # Telegram မှ Forward Source ပါလာလျှင် ယူမည်
    if message.forward_from_chat:
        target_group = message.forward_from_chat.id
    # Source ဖျောက်ထားလျှင် Cache ထဲမှ ပြန်ရှာမည်
    elif snippet in text_to_group:
        target_group = text_to_group[snippet]
        use_grab = text_to_grab.get(snippet, use_grab)

    if target_group:
        active_mapping[message.id] = (target_group, use_grab)
        print(f"📥 [Hand] Manual Forward မှတ်သားပြီးပါပြီ -> Group ID: {target_group} | Grab: {use_grab}")


# ==========================================
# ၃. Checker Bot Reply Handler (Auto & Hand နှစ်ခုစလုံးအတွက် အဖြေကို Group သို့ ပို့ပေးမည်)
# ==========================================
@pyrogram_app.on_message(filters.chat(CHECKER_BOT_ID) & filters.incoming)
async def checker_reply_listener(client, message):
    target_group = None
    use_grab = False

    # Reply ပြန်လာသော မက်ဆေ့ချ် ID ကို အခြေခံ၍ မူလ Group ကို ရှာမည်
    if message.reply_to_message:
        rep_id = message.reply_to_message.id
        if rep_id in active_mapping:
            target_group, use_grab = active_mapping[rep_id]

    # အကယ်၍ ID မတိုက်ဆိုင်ပါက နောက်ဆုံး မှတ်ထားသည့် Group ကို သုံးမည်
    if not target_group and active_mapping:
        last_key = list(active_mapping.keys())[-1]
        target_group, use_grab = active_mapping[last_key]

    if not target_group:
        print("❌ Spawn ဖြစ်ခဲ့သည့် Group ကို ရှာမတွေ့ပါ။")
        return

    text = message.text or message.caption or ""
    character_name = ""

    # Checker Bot ၏ အဖြေမှ နာမည်ကို ပုံစံအမျိုးမျိုးဖြင့် ရှာဖွေထုတ်ယူခြင်း
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
        # Username များနှင့် အမှိုက်များကို ဖြတ်ထုတ်မည်
        character_name = re.sub(r"@[a-zA-Z0-9_]+bot", "", character_name, flags=re.IGNORECASE).strip()
        
        prefix = "/grab" if use_grab else "/catch"
        final_cmd = f"{prefix} {character_name}"

        try:
            await client.send_message(target_group, final_cmd)
            print(f"🎯 Spawn ဖြစ်ခဲ့သော Group ({target_group}) သို့ အဖြေ အောင်မြင်စွာ ပို့ပြီးပါပြီ: {final_cmd}")
        except Exception as e:
            print(f"❌ အဖြေပို့၍မရပါ Error: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    pyrogram_app.run()

