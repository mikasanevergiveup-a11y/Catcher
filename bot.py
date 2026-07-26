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

# မူလ Group များကို တိကျစွာ မှတ်သားမည့် Dictionary (Key: Checker Bot ဆီပို့လိုက်သည့် Msg ID, Value: Group ID & Name)
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
    
    spawn_keywords = [
        "spawn", "appeared", "harem", "waifu", "husbando", 
        "grab", "catch", "character has spawned", "new waifu", "new husbando"
    ]
    
    is_spawn = any(kw in text for kw in spawn_keywords)

    if is_spawn:
        print(f"\n----------------------------------------")
        print(f"📌 [{group_name}] မှ Spawn ပုံ တွေ့ရှိပါပြီ!")
        target_checker_msg = None
        
        try:
            # ပထမနည်း - Forward လုပ်ကြည့်မည်
            fwd_msg = await message.forward(CHECKER_BOT_ID)
            target_checker_msg = fwd_msg.id
            print(f"✅ Checker Bot သို့ Forward ပြီးပါပြီ (ID: {target_checker_msg})")
        except Exception as e:
            print(f"⚠️ Forward Error ({e}) -> Copy ကူး၍ ပို့နေပါသည်...")
            try:
                # ဒုတိယနည်း - Copy ကူး၍ ပို့မည်
                copy_msg = await message.copy(CHECKER_BOT_ID)
                target_checker_msg = copy_msg.id
                print(f"✅ Checker Bot သို့ Copy ဖြင့် ပို့ပြီးပါပြီ (ID: {target_checker_msg})")
            except Exception as ex:
                print(f"❌ Copy လုပ်၍ မရပါ: {ex}")

        # ပို့လိုက်သည့် မက်ဆေ့ခ်ျ ID နှင့် မူလ Group ကို သေချာတွဲမှတ်မည်
        if target_checker_msg:
            forwarded_messages[target_checker_msg] = (message.chat.id, group_name)
            
            # မှတ်ဉာဏ်အလွန်များမသွားအောင် ပိုနေသော ပုံဟောင်းများကို ဖြတ်ထုတ်မည် (Old cleanup)
            if len(forwarded_messages) > 50:
                oldest_key = list(forwarded_messages.keys())[0]
                del forwarded_messages[oldest_key]

@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    msg_text = message.text or message.caption or ""
    print(f"\n📥 Checker Bot ဆီမှ စာလက်ခံရရှိပါသည်: {msg_text}")
    
    target_group = None
    group_name = "Unknown Group"
    
    # အဓိက အချက်: Checker Bot က reply ပြန်လာသည့် message ကို အခြေခံမှသာ မူလ Group ကို ရှာမည်
    if message.reply_to_message:
        reply_id = message.reply_to_message.id
        print(f"🔍 Reply လုပ်ထားသော Checker Message ID: {reply_id}")
        
        if reply_id in forwarded_messages:
            target_group, group_name = forwarded_messages[reply_id]
            print(f"🎯 တိကျသော မူလ Group တွေ့ရှိပါပြီ: {group_name} (ID: {target_group})")
        else:
            print(f"⚠️ ဤ Reply ID ({reply_id}) ကို မှတ်တမ်းထဲတွင် မတွေ့ရပါ။")
    else:
        print(f"⚠️ Checker Bot ဘက်မှ Reply လုပ်မထားပါ။")

    # Command ဖမ်းယူခြင်း (Regex)
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

    print(f"⚙️ ထွက်လာသော Command: {catch_cmd}")

    # တိကျမှန်ကန်သော Target Group ရှိမှသာ ပို့မည် (Fallback ဖြင့် အလဟဿ အခြား Group သို့ လုံးဝ မပို့တော့ပါ)
    if catch_cmd and target_group:
        print(f"📤 တိကျသော Group [{group_name}] သို့ '{catch_cmd}' ကို ပို့နေပါပြီ...")
        try:
            await client.send_message(target_group, catch_cmd)
            print(f"🎉 Group ထဲသို့ အောင်မြင်စွာ ပို့ပြီးပါပြီ!")
            
            # ပို့ပြီးပါက မှတ်တမ်းမှ ဖျက်မည်
            if message.reply_to_message and message.reply_to_message.id in forwarded_messages:
                del forwarded_messages[message.reply_to_message.id]
        except Exception as e:
            print(f"❌ Group ထဲသို့ ပို့၍မရပါ Error: {e}")
    else:
        print(f"❌ မူလ Group အတိအကျ မသိရှိရပါသဖြင့် မည်သည့် Group သို့မျှ စာမပို့ပါ။ (Group လွဲခြင်းမှ ကာကွယ်ထားသည်)")
    print(f"----------------------------------------\n")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("✅ Flask Server စတင်လိုက်ပါပြီ။")

    threading.Thread(target=ping_self, daemon=True).start()
    print("✅ 50s Self-ping စနစ် စတင်လိုက်ပါပြီ။")

    print("🤖 Userbot စတင် အလုပ်လုပ်နေပါပြီ...")
    pyrogram_app.run()

