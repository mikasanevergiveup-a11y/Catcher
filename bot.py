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

@pyrogram_app.on_message(filters.photo & ~filters.chat(CHECKER_BOT_ID))
async def on_spawn_message(client, message):
    text = (message.caption or message.text or "").lower()
    group_name = message.chat.title or str(message.chat.id)
    
    print(f"\n👀 [{group_name}] တွင် ပုံတစ်ပုံ တွေ့ရှိပါသည်၊ Checker ဆီ ပို့နေပါပြီ...")
    
    target_checker_msg_id = None
    use_grab = "grab" in text or "husbando" in text or "waifu" in text

    # နည်းလမ်း ၁ - ပုံမှန် Forward လုပ်ကြည့်မည်
    try:
        fwd_msg = await message.forward(CHECKER_BOT_ID)
        target_checker_msg_id = fwd_msg.id
        print("✅ Forward အောင်မြင်သည်!")
    except Exception as e_fwd:
        print(f"⚠️ Forward မရပါ ({e_fwd}) -> Copy ကူးကြည့်နေပါပြီ...")
        # နည်းလမ်း ၂ - Copy ကူး၍ ပို့ကြည့်မည်
        try:
            copy_msg = await message.copy(CHECKER_BOT_ID)
            target_checker_msg_id = copy_msg.id
            print("✅ Copy ဖြင့် ပို့ခြင်း အောင်မြင်သည်!")
        except Exception as e_copy:
            print(f"⚠️ Copy လည်း မရပါ ({e_copy}) -> ပုံကို Download ဆွဲ၍ တိုက်ရိုက် ပို့နေပါပြီ...")
            # နည်းလမ်း ၃ - ပုံကို ဖိုင်အဖြစ် ဒေါင်းပြီး တိုက်ရိုက် Upload တင်မည်
            try:
                photo_path = await message.download()
                sent_msg = await client.send_photo(CHECKER_BOT_ID, photo=photo_path, caption=message.caption or "")
                target_checker_msg_id = sent_msg.id
                if os.path.exists(photo_path):
                    os.remove(photo_path)
                print("✅ ပုံကို တိုက်ရိုက် Upload တင်ခြင်း အောင်မြင်သည်!")
            except Exception as e_dl:
                print(f"❌ အားလုံး မအောင်မြင်ပါ: {e_dl}")

    if target_checker_msg_id:
        forwarded_messages[target_checker_msg_id] = (message.chat.id, use_grab)
        if len(forwarded_messages) > 100:
            oldest_key = list(forwarded_messages.keys())[0]
            del forwarded_messages[oldest_key]

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
    
    if not target_group and forwarded_messages:
        last_key = list(forwarded_messages.keys())[-1]
        target_group, should_use_grab = forwarded_messages[last_key]
        del forwarded_messages[last_key]

    match = re.search(r"((?:/catch|/grab|/check)\s+[^\n]+)", msg_text, re.IGNORECASE)
    
    if match:
        catch_cmd = match.group(1).strip()
        if should_use_grab and catch_cmd.startswith("/catch"):
            catch_cmd = catch_cmd.replace("/catch", "/grab", 1)
        elif not should_use_grab and catch_cmd.startswith("/grab"):
            catch_cmd = catch_cmd.replace("/grab", "/catch", 1)
    else:
        match_alt = re.search(r"(?:Full|Name|Character|Hint)\s*[:\-]?\s*([^\n]+)", msg_text, re.IGNORECASE)
        if match_alt:
            val = match_alt.group(1).strip()
            prefix = "/grab" if should_use_grab else "/catch"
            catch_cmd = val if val.startswith("/") else f"{prefix} {val}"
        else:
            if msg_text.strip().startswith(("/", "/grab", "/catch")):
                catch_cmd = msg_text.strip()
            else:
                catch_cmd = None

    if catch_cmd and target_group:
        try:
            await client.send_message(target_group, catch_cmd)
            print(f"🎉 Group ထဲသို့ အဖြေပို့ပြီးပါပြီ: {catch_cmd}")
        except Exception as e:
            print(f"❌ အဖြေပို့၍မရပါ: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    pyrogram_app.run()

