import asyncio
import os
import re
from datetime import datetime

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7783091169"))
DB_PATH = "bot.db"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi. Railway Variables ga BOT_TOKEN qo'shing.")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# ----------------- DB -----------------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                joined_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                code TEXT PRIMARY KEY,
                channel TEXT NOT NULL,
                message_id INTEGER NOT NULL
            )
        """)
        await db.commit()


async def add_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, joined_at) VALUES (?, ?)",
            (user_id, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def add_movie(code: str, channel: str, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO movies (code, channel, message_id) VALUES (?, ?, ?)",
            (code, channel, message_id),
        )
        await db.commit()


async def get_movie(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT code, channel, message_id FROM movies WHERE code = ?",
            (code,),
        ) as cur:
            return await cur.fetchone()


async def delete_movie(code: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM movies WHERE code = ?", (code,))
        await db.commit()
        return cur.rowcount > 0


async def list_movies():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT code, channel, message_id FROM movies ORDER BY code ASC"
        ) as cur:
            return await cur.fetchall()


async def count_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def count_movies() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM movies") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            return await cur.fetchall()


# ----------------- Helpers -----------------
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def parse_public_channel_link(link: str):
    """
    Qabul qiladi:
    https://t.me/kanalname/123
    http://t.me/kanalname/123
    t.me/kanalname/123
    @kanalname/123
    """
    link = link.strip()

    m = re.match(r"^(?:https?://)?t\.me/([A-Za-z0-9_]+)/(\d+)$", link)
    if m:
        return f"@{m.group(1)}", int(m.group(2))

    m = re.match(r"^@([A-Za-z0-9_]+)/(\d+)$", link)
    if m:
        return f"@{m.group(1)}", int(m.group(2))

    return None, None


def admin_help_text():
    return (
        "👨‍💼 <b>Admin buyruqlari</b>\n\n"
        "<code>/add KOD LINK</code>\n"
        "Misol: <code>/add 1234 https://t.me/Kino_bor_channel/15</code>\n\n"
        "<code>/del KOD</code>\n"
        "Misol: <code>/del 1234</code>\n\n"
        "<code>/list</code>\n"
        "<code>/stats</code>\n"
        "<code>/broadcast matn</code>"
    )


# ----------------- Handlers -----------------
@dp.message(CommandStart())
async def start(message: Message):
    if message.chat.type != "private":
        return

    await add_user(message.from_user.id)

    text = (
        "🎬 <b>Kino botga xush kelibsiz!</b>\n\n"
        "Kino kodini yuboring, men kanal postini chiqaraman."
    )
    if is_admin(message.from_user.id):
        text += "\n\n" + admin_help_text()

    await message.answer(text)


@dp.message(Command("help"))
async def help_cmd(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Kino kodini yuboring.")
        return
    await message.answer(admin_help_text())


@dp.message(Command("add"))
async def add_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "❌ Noto'g'ri format.\n"
            "To'g'ri:\n"
            "<code>/add 1234 https://t.me/Kino_bor_channel/15</code>"
        )
        return

    code = args[1].strip()
    link = args[2].strip()

    channel, message_id = parse_public_channel_link(link)
    if not channel:
        await message.answer(
            "❌ Link noto'g'ri.\n"
            "Faqat public kanal linki kerak:\n"
            "<code>https://t.me/Kino_bor_channel/15</code>"
        )
        return

    await add_movie(code, channel, message_id)
    await message.answer(
        "✅ Saqlandi!\n\n"
        f"Kod: <code>{code}</code>\n"
        f"Kanal: <code>{channel}</code>\n"
        f"Post ID: <code>{message_id}</code>"
    )


@dp.message(Command("del"))
async def del_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Format: <code>/del 1234</code>")
        return

    code = args[1].strip()
    deleted = await delete_movie(code)

    if deleted:
        await message.answer(f"✅ O'chirildi: <code>{code}</code>")
    else:
        await message.answer(f"❌ Bunday kod topilmadi: <code>{code}</code>")


@dp.message(Command("list"))
async def list_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    rows = await list_movies()
    if not rows:
        await message.answer("Hozircha kino yo'q.")
        return

    text = "<b>Kinolar ro'yxati</b>\n\n"
    for row in rows[:50]:
        text += f"• <code>{row['code']}</code> → <code>{row['channel']}/{row['message_id']}</code>\n"

    if len(rows) > 50:
        text += f"\n... yana {len(rows) - 50} ta bor."

    await message.answer(text)


@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    users = await count_users()
    movies = await count_movies()

    await message.answer(
        "<b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{users}</b>\n"
        f"🎬 Kinolar: <b>{movies}</b>"
    )


@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Format: <code>/broadcast Salom hammaga</code>")
        return

    text = args[1].strip()
    users = await get_all_users()

    ok = 0
    fail = 0

    await message.answer(f"Yuborish boshlandi. Jami user: {len(users)}")

    for row in users:
        user_id = row[0]
        try:
            await bot.send_message(user_id, text)
            ok += 1
            await asyncio.sleep(0.03)
        except Exception:
            fail += 1

    await message.answer(f"✅ Tugadi.\nYuborildi: {ok}\nXato: {fail}")


@dp.message(F.text)
async def on_text(message: Message):
    if message.chat.type != "private":
        return

    await add_user(message.from_user.id)

    code = message.text.strip()
    movie = await get_movie(code)

    if not movie:
        await message.answer("❌ Bunday kod topilmadi.")
        return

    try:
        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=movie["channel"],
            message_id=movie["message_id"],
        )
    except Exception:
        await message.answer(
            "❌ Kinoni yuborib bo'lmadi.\n"
            "Sabab: kanalga bot admin qilinganini va post link to'g'riligini tekshiring."
        )


# ----------------- Main -----------------
async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
