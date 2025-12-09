import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def main():
    bot = Bot(BOT_TOKEN)
    updates = await bot.get_updates()
    
    for update in updates:
        if update.message and update.message.chat.type in ['group', 'supergroup']:
            print("Group name:", update.message.chat.title)
            print("Group ID:", update.message.chat.id)

if __name__ == "__main__":
    asyncio.run(main())
