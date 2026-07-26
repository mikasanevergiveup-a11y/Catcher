import os
import re
import threading
import time
import requests
from flask import Flask
from pyrogram import Client, filters

# Configuration from Environment Variables
API_ID = int(os.environ.get("API_ID", "38612444"))
API_HASH = os.environ.get("API_HASH", "49d750a1b3ae94cdec9a0df20535c3d9")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

# Forward လုပ်ရမည့် Checker Bot ID
CHECKER_BOT_ID = 8506436817

# Forward လုပ်ထားသော/Copy လုပ်ထားသော မက်ဆေ့ခ်ျ ID နှင့် Group ID ကို မှတ်သားမည့် Dictionary
forwarded_messages = {}

# Flask App (Render Web Service အတွက်)
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
    """Render မအိပ်သွားစေရန် ၅၀ စက္ကန့်တစ်ခါ Self-ping လုပ်ပေးမည်"""
    time.sleep(10)
    while True:
        url = os.environ.get("RENDER_EXTERNAL_URL", "")
        if url:
            try:
                requests.get(f"{url}/health", timeout=10)
            except Exception:
                pass
        time.sleep(50)

# Pyrogram Client Setup
pyrogram_app = Client("autocatch_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Checker Bot မှလွဲ၍ မည်သည့်နေရာမှမဆို ပုံ (Photo) ပါလာပါက စစ်ဆေးမည်
@pyrogram_app.on_message(filters.photo & ~filters.chat(CHECKER_BOT_ID))
async def on_spawn_message(client, message):
    text = (message.caption or message.text or "").lower()
    group_name = message.chat.title or str(message.chat.id)
    
    # ပုံထဲပါရှိသော စာသားပုံစံအမျိုးမျိုးကို စစ်ဆေးခြင်း
    spawn_keywords = [
        "spawn", "appeared", "harem", "waifu", "husbando", 
        "grab", "catch", "character has spawned", "new waifu", "new husbando"
    ]
    
    is_spawn = any(kw in text for kw in spawn_keywords)

    if is_spawn:
        print(f"\n----------------------------------------")
        print(f"📌 [{group_name}] မှ Card Bot ၏ Spawn ပုံကို တွေ့ရှိပါပြီ!")
        print(f"🚀 Checker Bot ဆီသို့ Instant ပို့နေပါသည်...")
        try:
            # ပထမနည်း - တိုက်ရိုက် Forward လုပ်ကြည့်မည်
            fwd_msg = await message.forward(CHECKER_BOT_ID)
            forwarded_messages[fwd_msg.id] = (message.chat.id, group_name)
            print(f"✅ Forward အောင်မြင်ပါသည်။")
        except Exception as e:
            # Group က Forward ပိတ်ထားပါက ဤနေရာမှ Copy ကူး၍ ပို့မည်
            print(f"⚠️ Forward လုပ်၍မရပါ ({e}) -> ပုံကို Copy ကူး၍ ပို့နေပါသည်...")
            try:
                copy_msg = await message.copy(CHECKER_BOT_ID)
                forwarded_messages[copy_msg.id] = (message.chat.id, group_name)
                print(f"✅ Copy ကူး၍ ပို့ခြင်း အောင်မြင်ပါသည်။")
            except Exception as ex:
                print(f"❌ Copy လုပ်၍လည်း မရပါ: {ex}")

@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    msg_text = message.text or message.caption or ""
    
    target_group = None
    group_name = "Unknown Group"
    
    if message.reply_to_message:
        data = forwarded_messages.get(message.reply_to_message.id)
        if data:
            target_group, group_name = data

    if not target_group and forwarded_messages:
        target_group, group_name = list(forwarded_messages.values())[-1]

    # Checker Bot မှ ပို့ပေးသော ကွန်မန်များကို ရှာဖွေခြင်း
    match = re.search(r"((?:/catch|/grab|/check)\s+[^\n]+)", msg_text, re.IGNORECASE)
    
    if match:
        catch_cmd = match.group(1).strip()
    else:
        match_alt = re.search(r"(?:Full|Name|Character)\s*[:\-]?\s*([^\n]+)", msg_text, re.IGNORECASE)
        if match_alt:
            val = match_alt.group(1).strip()
            catch_cmd = val if val.startswith("/") else f"/catch {val}"
        else:
            catch_cmd = msg_text.strip() if msg_text.strip().startswith("/") else None

    if catch_cmd and target_group:
        print(f"📤 [{group_name}] သို့ '{catch_cmd}' လို့ ပို့ပြီးပါပြီ...")
        try:
            await client.send_message(target_group, catch_cmd)
            print(f"🎉 အောင်မြင်စွာ ပြီးဆုံးပါပြီ!")
            if message.reply_to_message and message.reply_to_message.id in forwarded_messages:
                del forwarded_messages[message.reply_to_message.id]
        except Exception as e:
            print(f"❌ Group ထဲသို့ ပို့၍မရပါ Error: {e}")
        print(f"----------------------------------------\n")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("✅ Flask Server စတင်လိုက်ပါပြီ။")

    threading.Thread(target=ping_self, daemon=True).start()
    print("✅ 50s Self-ping စနစ် စတင်လိုက်ပါပြီ။")

    print("🤖 Userbot စတင် အလုပ်လုပ်နေပါပြီ...")
    pyrogram_app.run()
    
