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
    
    spawn_keywords = [
        "spawn", "appeared", "harem", "waifu", "husbando", 
        "grab", "catch", "character has spawned", "new waifu", "new husbando"
    ]
    
    is_spawn = any(kw in text for kw in spawn_keywords) or len(text) == 0

    if is_spawn:
        print(f"📌 [{group_name}] Spawn ပုံ တွေ့ရှိပါသည် Checker သို့ ပို့မည်...")
        try:
            fwd_msg = await message.forward(CHECKER_BOT_ID)
            # Forward လုပ်လိုက်သော Checker Bot ဘက်မှ Message ID ကို မူလ Group ID နှင့် အတိအကျ တွဲမှတ်မည်
            forwarded_messages[fwd_msg.id] = (message.chat.id, group_name)
            print(f"✅ Forward အောင်မြင်သည် (Checker Msg ID: {fwd_msg.id})")
        except Exception as e:
            print(f"⚠️ Forward Error ({e}) -> Copy ကူး၍ ပို့နေပါသည်...")
            try:
                copy_msg = await message.copy(CHECKER_BOT_ID)
                forwarded_messages[copy_msg.id] = (message.chat.id, group_name)
                print(f"✅ Copy ဖြင့် ပို့ခြင်း အောင်မြင်သည် (Checker Msg ID: {copy_msg.id})")
            except Exception as ex:
                print(f"❌ ပို့၍မရပါ: {ex}")

        # မှတ်ဉာဏ် မပိတ်ဆို့စေရန် မှတ်တမ်းအဟောင်းများကို ထိန်းသိမ်းမည်
        if len(forwarded_messages) > 100:
            oldest_key = list(forwarded_messages.keys())[0]
            del forwarded_messages[oldest_key]

@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    msg_text = message.text or message.caption or ""
    print(f"📥 Checker Bot မှ စာလာပါပြီ: {msg_text}")
    
    target_group = None
    group_name = "Unknown Group"
    
    # ဤနေရာသည် အဓိကအချက်ဖြစ်သည် - Checker Bot က ဘယ် မက်ဆေ့ခ်ျကို Reply လုပ်လာသလဲ အတိအကျရှာမည်
    if message.reply_to_message:
        reply_id = message.reply_to_message.id
        if reply_id in forwarded_messages:
            target_group, group_name = forwarded_messages[reply_id]
            print(f"🎯 တိကျသော Reply ချိတ်ဆက်မှု တွေ့ရှိသည်: {group_name} (ID: {target_group})")
            # အသုံးပြုပြီးသား ID ကို မှတ်တမ်းမှ ဖျက်ထုတ်မည် (အခြားအမှားမပါအောင်)
            del forwarded_messages[reply_id]
        else:
            print(f"⚠️ Reply ID ({reply_id}) ကို မှတ်တမ်းထဲတွင် မတွေ့ရပါ။")
    else:
        print(f"⚠️ Checker Bot ဘက်မှ Reply လုပ်မထားပါ။")

    match = re.search(r"((?:/catch|/grab|/check)\s+[^\n]+)", msg_text, re.IGNORECASE)
    
    if match:
        catch_cmd = match.group(1).strip()
    else:
        match_alt = re.search(r"(?:Full|Name|Character|Hint)\s*[:\-]?\s*([^\n]+)", msg_text, re.IGNORECASE)
        if match_alt:
            val = match_alt.group(1).strip()
            catch_cmd = val if val.startswith("/") else f"/catch {val}"
        else:
            if msg_text.strip().startswith(("/", "/grab", "/catch")):
                catch_cmd = msg_text.strip()
            else:
                catch_cmd = None

    # တိကျမှန်ကန်သော Reply ချိတ်ဆက်မှုမှ ရလာသည့် Group ဆီသို့သာ ပို့မည် (Group လွဲခြင်း လုံးဝ ကာကွယ်ပြီး)
    if catch_cmd and target_group:
        print(f"📤 [{group_name}] သို့ '{catch_cmd}' ကို ပို့နေပါပြီ...")
        try:
            await client.send_message(target_group, catch_cmd)
            print(f"🎉 အောင်မြင်စွာ ပို့ပြီးပါပြီ!")
        except Exception as e:
            print(f"❌ ပို့၍မရပါ Error: {e}")
    else:
        print(f"❌ မှန်ကန်သော Reply Target မရှိပါသဖြင့် ကျော်လိုက်ပါသည်။ (အခြား Group သို့ လွဲမှားပို့ခြင်း မရှိပါ)")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    print("🤖 Userbot စတင် အလုပ်လုပ်နေပါပြီ...")
    pyrogram_app.run()

