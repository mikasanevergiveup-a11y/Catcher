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
# ၁။ Automatic System (Group ထဲမှ ပုံနှင့်စာများကို သေချာဖမ်းယူပေးမည်)
# ==========================================
@pyrogram_app.on_message(filters.incoming & (filters.photo | filters.document))
async def auto_spawn_listener(client, message):
    # Group ဟုတ်မဟုတ် Chat ID (ငွေကြေး/အနုတ်လက္ခဏာ) ဖြင့် အတိအကျ စစ်ဆေးမည်
    if not message.chat or message.chat.id >= 0:
        return

    text = (message.caption or message.text or "").lower()
    
    # Debug ကို Render Logs ထဲတွင် ကြည့်ရန်
    print(f"🔍 [Group Message Detected] Chat ID: {message.chat.id} | Text: {text[:40]}...")

    if not text:
        return

    # Spawn ဟုတ်မဟုတ် ကျယ်ကျယ်ပြန့်ပြန့် စစ်ဆေးခြင်း
    keywords = ["waifu", "husbando", "grab", "spawned", "catch", "character", "harem", "spawn"]
    is_spawn = any(kw in text for kw in keywords)
    
    if not is_spawn:
        return

    use_grab = any(kw in text for kw in ["waifu", "husbando", "grab"])

    group_id = message.chat.id
    snippet = text.replace('\n', ' ')[:50].strip()

    text_to_group[snippet] = group_id
    text_to_grab[snippet] = use_grab

    print(f"\n⚡ [Auto Success] Group ({message.chat.title or group_id}) တွင် Spawn တွေ့ရှိပါပြီ! Checker ဆီသို့ ပို့နေပါပြီ...")

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
# ၂. Manual / Hand System (ဘာမှမပြင်ဘဲ မူလအတိုင်း အသေထားရှိသည်)
# ==========================================
@pyrogram_app.on_message(filters.chat(CHECKER_BOT_ID) & filters.outgoing)
async def manual_forward_listener(client, message):
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
        print(f"📥 [Hand] Manual Forward မှတ်သားပြီးပါပြီ -> Group ID: {target_group} | Grab: {use_grab}")


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

