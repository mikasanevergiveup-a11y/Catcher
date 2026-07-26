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

# Card Reader (Checker Bot) ၏ ID
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

# Checker Bot မှလွဲ၍ မည်သည့် Group မှမဆို ပုံ (Photo) ပါလာပါက ချက်ချင်းဖမ်းမည်
@pyrogram_app.on_message(filters.photo & ~filters.chat(CHECKER_BOT_ID))
async def on_spawn_message(client, message):
    text = (message.caption or message.text or "").lower()
    group_name = message.chat.title or str(message.chat.id)
    
    print(f"\n👀 [{group_name}] တွင် ပုံတစ်ပုံ တွေ့ရှိပါသည်!")

    # မည်သည့် Bot ၏ Spawn ပုံမဆို ချက်ချင်း Checker Bot ဆီသို့ Forward / Copy လုပ်မည်
    target_checker_msg = None
    try:
        fwd_msg = await message.forward(CHECKER_BOT_ID)
        target_checker_msg = fwd_msg.id
        print(f"✅ Forward အောင်မြင်သည် (ID: {target_checker_msg})")
    except Exception as e:
        print(f"⚠️ Forward Error ({e}) -> Copy ကူး၍ ပို့နေပါသည်...")
        try:
            copy_msg = await message.copy(CHECKER_BOT_ID)
            target_checker_msg = copy_msg.id
            print(f"✅ Copy ဖြင့် ပို့ခြင်း အောင်မြင်သည် (ID: {target_checker_msg})")
        except Exception as ex:
            print(f"❌ ပို့၍မရပါ: {ex}")

    if target_checker_msg:
        # မူလ Group ရဲ့ Caption ထဲမှာ /grab သုံးရမလား /catch သုံးရမလားပါ မှတ်ထားမည်
        use_grab = "grab" in text or "husbando" in text or "waifu" in text
        forwarded_messages[target_checker_msg] = (message.chat.id, group_name, use_grab)
        
        if len(forwarded_messages) > 100:
            oldest_key = list(forwarded_messages.keys())[0]
            del forwarded_messages[oldest_key]

@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    msg_text = message.text or message.caption or ""
    print(f"\n📥 Checker Bot မှ အဖြေလာပါပြီ: {msg_text}")
    
    target_group = None
    group_name = "Unknown Group"
    should_use_grab = False
    
    if message.reply_to_message:
        reply_id = message.reply_to_message.id
        if reply_id in forwarded_messages:
            target_group, group_name, should_use_grab = forwarded_messages[reply_id]
            print(f"🎯 တိကျသော Group တွေ့ရှိသည်: {group_name} (Grab mode: {should_use_grab})")
            del forwarded_messages[reply_id]
    
    if not target_group and forwarded_messages:
        last_key = list(forwarded_messages.keys())[-1]
        target_group, group_name, should_use_grab = forwarded_messages[last_key]
        del forwarded_messages[last_key]
        print(f"📌 နောက်ဆုံး မှတ်ထားသော Group ကို သုံးမည်: {group_name}")

    # Checker Bot ဆီက ထွက်လာတဲ့ စာသားထဲက Character နာမည် သို့မဟုတ် Command ကို ဖြုတ်ထုတ်မည်
    match = re.search(r"((?:/catch|/grab|/check)\s+[^\n]+)", msg_text, re.IGNORECASE)
    
    if match:
        catch_cmd = match.group(1).strip()
        # မူလ Group က /grab သုံးရမည့် Bot ဖြစ်ပြီး အဖြေက /catch ဖြစ်နေပါက /grab သို့ ပြောင်းပေးမည်
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
        print(f"📤 [{group_name}] သို့ '{catch_cmd}' ကို ပို့နေပါပြီ...")
        try:
            await client.send_message(target_group, catch_cmd)
            print(f"🎉 အောင်မြင်စွာ ပို့ပြီးပါပြီ!")
        except Exception as e:
            print(f"❌ ပို့၍မရပါ Error: {e}")
    else:
        print(f"❌ Command သို့မဟုတ် Target Group မရှိပါသဖြင့် ကျော်လိုက်ပါသည်။")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    print("🤖 Userbot စတင် အလုပ်လုပ်နေပါပြီ...")
    pyrogram_app.run()

