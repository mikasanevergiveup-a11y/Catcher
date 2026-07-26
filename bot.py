import os
import re
import asyncio
from flask import Flask
from pyrogram import Client, filters, idle

API_ID = int(os.environ.get("API_ID", "38612444"))
API_HASH = os.environ.get("API_HASH", "49d750a1b3ae94cdec9a0df20535c3d9")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
CHECKER_BOT_ID = 8506436817

pending_groups = []

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is Alive!", 200

@app_flask.route('/health')
def health():
    return "OK", 200

pyrogram_app = Client(
    "autocatch_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@pyrogram_app.on_message()
async def on_spawn_message(client, message):
    try:
        if not message.chat:
            return
            
        chat_id = message.chat.id
        text = (message.text or message.caption or "").lower()
        
        spawn_keywords = ["appeared", "spawned", "character", "harem", "guess", "catch", "grab", "waifu", "hurry"]
        
        if message.photo and any(kw in text for kw in spawn_keywords):
            print(f"🎯 Group [{chat_id}] တွင် Spawn တွေ့ပါပြီ! Checker သို့ Forward လုပ်နေသည်...")
            pending_groups.append(chat_id)
            # send_message (သို့) forward လုပ်သည့်အခါ Peer ID Error မတက်စေရန် get_chat သုံးပြီး cache လုပ်မည်
            await client.get_chat(chat_id)
            await message.forward(CHECKER_BOT_ID)
    except Exception as e:
        print(f"❌ Spawn Error: {e}")

@pyrogram_app.on_message(filters.user(CHECKER_BOT_ID))
async def on_checker_reply(client, message):
    try:
        global pending_groups
        msg_text = message.text or message.caption or ""
        print(f"📩 Checker Reply:\n{msg_text}")
        
        cmd_to_send = None
        match_cmd = re.search(r"((?:/catch|/guess|/grab|/hunt|/collect)\s+[^\n]+)", msg_text, re.IGNORECASE)
        if match_cmd:
            cmd_to_send = match_cmd.group(1).strip()
        else:
            match_alt = re.search(r"(?:Full|Name|Character|Result|Hint)\s*[:\-]?\s*([^\n]+)", msg_text, re.IGNORECASE)
            if match_alt:
                raw_val = match_alt.group(1).strip()
                if raw_val.startswith("/") or raw_val.startswith("!"):
                    cmd_to_send = raw_val
                else:
                    if "grab" in msg_text.lower():
                        prefix = "/grab"
                    elif "guess" in msg_text.lower():
                        prefix = "/guess"
                    else:
                        prefix = "/catch"
                    cmd_to_send = f"{prefix} {raw_val}"

        if cmd_to_send and pending_groups:
            target_group = pending_groups.pop(0)
            print(f"📤 Group [{target_group}] သို့ ပို့မည်: '{cmd_to_send}'")
            await client.send_message(target_group, cmd_to_send)
    except Exception as e:
        print(f"❌ Checker Reply Error: {e}")

async def main():
    port = int(os.environ.get("PORT", 10000))
    print("🤖 Pyrogram Userbot စတင်နေပါပြီ...")
    
    await pyrogram_app.start()
    
    # Userbot ရောက်ရှိနေသော Group များနှင့် Dialogs များကို Cache တည်ဆောက်မည် (Peer ID Error ကာကွယ်ရန်)
    print("🔄 Group များနှင့် Chat များကို Cache လုပ်နေပါပြီ...")
    try:
        async for _ in pyrogram_app.get_dialogs():
            pass
        print("✅ Cache တည်ဆောက်ပြီးပါပြီ။ Bot အသင့်ဖြစ်ပါပြီ။")
    except Exception as e:
        print(f"⚠️ Cache Error: {e}")
    
    import hypercorn.asyncio
    from hypercorn.config import Config
    
    config = Config()
    config.bind = [f"0.0.0.0:{port}"]
    
    await asyncio.gather(
        hypercorn.asyncio.serve(app_flask, config),
        idle()
    )
    await pyrogram_app.stop()

if __name__ == "__main__":
    asyncio.run(main())

