import os
import time
import asyncio
import uvloop
from pyrogram import types, Client
from pyrogram.errors import FloodWait
from aiohttp import web
from typing import Union, Optional, AsyncGenerator
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Local imports
from web import web_app
from info import LOG_CHANNEL, API_ID, API_HASH, BOT_TOKEN, PORT, BIN_CHANNEL, ADMINS, DATABASE_URL
from utils import temp, get_readable_time
from database.users_chats_db import db
from database.ia_filterdb import Media

# Install uvloop for faster event loop
uvloop.install()

class Bot(Client):
    def __init__(self):
        super().__init__(
            name='Auto_Filter_Bot',
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"}
        )

    async def start(self):
        temp.START_TIME = time.time()
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        client = MongoClient(DATABASE_URL, server_api=ServerApi('1'))
        try:
            client.admin.command('ping')
            print("Successfully connected to MongoDB!")
        except Exception as e:
            print("Failed to connect to MongoDB:", e)
            exit()

        await super().start()
        
        # Restart handling
        if os.path.exists('restart.txt'):
            with open("restart.txt") as file:
                chat_id, msg_id = map(int, file)
            try:
                await self.edit_message_text(chat_id=chat_id, message_id=msg_id, text='Restarted Successfully!')
            except:
                pass
            os.remove('restart.txt')
        
        temp.BOT = self
        await Media.ensure_indexes()
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name

        print(f"{me.first_name} is now started 🤗")
        
        # Start web server
        app = web.AppRunner(web_app)
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()

        # Send messages to channels
        try:
            await self.send_message(chat_id=LOG_CHANNEL, text=f"<b>{me.mention} Restarted! 🤖</b>")
        except:
            print("Error - Ensure bot is admin in LOG_CHANNEL. Exiting...")
            exit()
        try:
            test_message = await self.send_message(chat_id=BIN_CHANNEL, text="Test")
            await test_message.delete()
        except:
            print("Error - Ensure bot is admin in BIN_CHANNEL. Exiting...")
            exit()

        for admin in ADMINS:
            await self.send_message(chat_id=admin, text="<b>✅ ʙᴏᴛ ʀᴇsᴛᴀʀᴛᴇᴅ</b>")

    async def stop(self, *args):
        await super().stop()
        print("Bot Stopped! Bye...")

    async def iter_messages(self, chat_id: Union[int, str], limit: int, offset: int = 0) -> Optional[AsyncGenerator["types.Message", None]]:
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1

# Create Bot instance
app = Bot()

async def main():
    try:
        await app.run()
    except FloodWait as e:
        wait_time = e.value
        print(f"FloodWait occurred. Sleeping for {get_readable_time(wait_time)}")
        await asyncio.sleep(wait_time)
        print("Resuming bot...")
        await main()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await app.stop()

# Run the bot
if __name__ == "__main__":
    asyncio.run(main())
