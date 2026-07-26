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

# Memory Caches
active_mapping = {}      
text_to_group = {}       
text_to_grab = {}        

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
# ၁။ Fixed Auto System (စာသားများကို Entities ပါမကျန် အပြည့်အစုံ ဖတ်ပေးမည်)
# ==========================================
@pyrogram_app.on_message(filters.group & (filters.photo | filters.document))
async def robust_auto_listener(client, message):
    if message.from_user and message.from_user.is_self:
        return

    # Caption သို့မဟုတ် Text ကို Entities များပါမကျန် အစအဆုံး ဆွဲထုတ်ခြင်း
    raw_text = message.caption or message.text or ""
    
    # အကယ်၍ Caption မပါလာခဲ့လျှင်တောင် Message Object ထဲက entities များကို စာသားအဖြစ် ပြန်ဖော်မည်
    if not raw_text and message.caption_entities:
        raw_text = "".join([message.text[ent.offset:ent.offset+ent.length] for ent in message.caption_entities])

    text = raw_text.lower()
    print(f"🔍 [Auto Scan] Group ID: {message.chat.id} | Read Text: {text[:60]}...")

    # Spawn ဟုတ်မဟုတ် သေချာစေရန် Keywords များကို ကျယ်ကျယ်ပြန့်ပြန့် စစ်ဆေးမည်
    keywords = ["waifu", "husbando", "grab", "spawned", "catch", "character", "harem", "spawn", "chat!", "here"]
    is_spawn = any(kw in text for kw in keywords)
    
    # အကယ်၍ Keyword မတွေ့ရင်တောင် ပုံနှင့်အတူ Bot တစ်ခုခုက ပို့ထားတာသေချာလျှင် အလိုအလျောက် ပို့ပေးရန် (Optional - လိုအပ်ပါက ဖွင့်နိုင်သည်)
    if not is_spawn and message.from_user and message.from_user.is_bot:
        is_spawn = True  # Bot က ပို့တဲ့ပုံမှန်န် ပုံမှန်ား Spawn ဖြစ်နိုင်ခြေများလို့ ဖမ်းမည်

    if not is_spawn:
        return

    use_grab = any(kw in text for kw in ["waifu", "husbando", "grab"])
    group_id = message.chat.id
    snippet = text.replace('\n', ' ')[:50].strip()
    if not snippet:
        snippet = "spawn_image_fallback"

    text_to_group[snippet] = group_id
    text_to_grab[snippet] = use_grab

    print(f"\n⚡ [Auto Triggered] Group ({group_id}) တွင် Spawn တွေ့ရှိပါပြီ! Checker ဆီ ပို့နေပါပြီ...")

    target_checker_msg_id = None
    try:
        fwd = await message.forward(CHECKER_BOT_ID)
        target_checker_msg_id = fwd.id
        print("✅ Auto-Forward အောင်မြင်သည်!")
    except Exception as e1:
        try:
            cpy = await message.copy(CHECKER_BOT_ID)
            target_checker_msg_id = cpy.id
            print("✅ Auto-Copy အောင်မြင်သည်!")
        except Exception as e2:
            print(f"❌ Auto ပို့၍မရပါ Error: {e1} | {e2}")

    if target_checker_msg_id:
        active_mapping[target_checker_msg_id] = (group_id, use_grab)

    if len(active_mapping) > 200:
        active_mapping.pop(next(iter(active_mapping)))
    if len(text_to_group) > 200:
        text_to_group.pop(next(iter(text_to_group)))


# ==========================================
# ၂. Manual / Hand System (မူလအတိုင်း အကောင်းဆုံး အလုပ်လုပ်မည်)
# ==========================================
@pyrogram_app.on_message(filters.outgoing)
async def manual_forward_listener(client, message):
    if message.chat.id != CHECKER_BOT_ID:
        return

    text = (message.caption or message.text or "").lower()
    snippet = text.replace('\n', ' ')[:50].strip()

    target_group = None
    use_grab = "waifu" in text or "husbando" in text or "grab" in text

    if message.forward_from_chat:
        target_group = message.forward_from_chat.id
    elif snippet in text_to_group:
        target_group = text_to_group[snippet]
        use_grab = text_to_grab.get(snippet, use_grab)

    if target_group:
        active_mapping[message.id] = (target_group, use_grab)
        print(f"📥 [Hand] Manual Forward မှတ်သားပြီးပါပြီ -> Target Group ID: {target_group} | Grab: {use_grab}")


# ==========================================
# ၃. Checker Bot Reply Handler (အဖြေကို မူလ Group ဆီသို့ အတိအကျ ပို့ပေးမည်)
# ==========================================
@pyrogram_app.on_message(filters.chat(CHECKER_BOT_ID) & filters.incoming)
async def checker_reply_listener(client, message):
    target_group = None
    use_grab = False

    if message.reply_to_message:
        rep_id = message.reply_to_message.id
        if rep_id in active_mapping:
            target_group, use_grab = active_mapping[rep_id]

    if not target_group and active_mapping:
        last_key = list(active_mapping.keys())[-1]
        target_group, use_grab = active_mapping[last_key]

    if not target_group:
        print("❌ Spawn ဖြစ်ခဲ့သည့် Group ကို ရှာမတွေ့ပါ။")
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
            print(f"🎯 Spawn ဖြစ်ခဲ့သော Group ({target_group}) သို့ အဖြေ အောင်မြင်စွာ ပို့ပြီးပါပြီ: {final_cmd}")
        except Exception as e:
            print(f"❌ အဖြေပို့၍မရပါ Error: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    pyrogram_app.run()

