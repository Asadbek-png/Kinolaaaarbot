import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(TOKEN)
dp = Dispatcher()

# Sinov uchun
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("🎬 Kinolar botiga xush kelibsiz!\nKino kodini yuboring.")

@dp.message(F.text)
async def kino_kodi(message: Message):
    await message.answer(f"Siz yuborgan kod: {message.text}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
