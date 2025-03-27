import asyncio
import os
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

import db
from keyboards import main_menu_keyboard

logging.basicConfig(level=logging.INFO)

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message):
    user = await db.check_user(message.from_user.id)
    if not user:
        await db.add_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )
    await message.answer(
        f"Привет, {message.from_user.first_name}! Я школьный бот. Чем могу помочь?",
        reply_markup=main_menu_keyboard
    )


@router.message(F.text == "📅 Расписание")
async def schedule_handler(message: Message):
    await message.answer("Введите класс и день недели (например, '7A Понедельник'):")


@router.message(F.text.regexp(r'^\d+[АA]\s+\w+$'))
async def process_schedule(message: Message):
    class_name, day = message.text.split(maxsplit=1)
    lessons = await db.get_schedule(class_name, day)
    if lessons:
        await message.answer(f"📚 Расписание для {class_name} на {day}:\n{lessons}")
    else:
        await message.answer("❌ Расписание не найдено. Проверьте правильность ввода.")


@router.message(F.text == "📌 События")
async def events_handler(message: Message):
    try:
        events = await db.get_events()
        print(f"DEBUG: Получены события из БД: {events}")

        if not events:
            await message.answer("На данный момент нет запланированных событий.")
            return

        response = "📅 Все события:\n\n"
        today = datetime.now().date()

        for event in events:
            event_date = event["event_date"]

            if isinstance(event_date, str):
                event_date = datetime.strptime(event_date, "%Y-%m-%d").date()

            formatted_date = event_date.strftime("%d.%m.%Y")

            status = "✅ Предстоящее" if event_date >= today else "❌ Прошедшее"

            response += f"{status} {event['event_name']} ({formatted_date})\n"
            response += f"   {event['description']}\n\n"

        await message.answer(response)
    except Exception as e:
        print(f"Ошибка в обработчике событий: {e}")
        await message.answer("Произошла ошибка при получении событий.")


@router.message(F.text == "ℹ️ FAQ")
async def faq_handler(message: Message):
    faq_items = [
        "❓ Когда родительское собрание? - Ближайшее собрание 05.04.2024",
        "❓ Как связаться с учителем? - Через классного руководителя",
        "❓ Какое расписание? - Введите класс и день недели"
    ]
    await message.answer("\n\n".join(faq_items))


async def main():
    print("Проверка подключения к БД...")
    await db.create_pool()

    test_events = await db.get_events()
    print(f"Тестовый запрос событий: {test_events}")


async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    await db.create_pool()

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    try:
        await dp.start_polling(bot)
    finally:
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(main())