import asyncio
import os
import logging

import openai
from config import AI_API_KEY
from openai import OpenAI, OpenAIError
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ai_utils import chat_with_ai
import db
from keyboards import main_menu_keyboard
import config


logging.basicConfig(level=logging.INFO)
router = Router()
bot = Bot(token=os.getenv("BOT_TOKEN"))
openai.api_key = AI_API_KEY



class AdminStates(StatesGroup):
    waiting_password = State()
    waiting_schedule = State()
    waiting_event = State()


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
            response += f"{status} {event['event_name']} ({formatted_date})\n{event['description']}\n\n"

        await message.answer(response)
    except Exception as e:
        print(f"Ошибка в обработчике событий: {e}")
        await message.answer("Произошла ошибка при получении событий.")


# @router.message(F.text == "ℹ️ FAQ")
# async def faq_handler(message: Message):
#     await message.answer("Вы можете спросить о:\n- Расписании\n- Событиях\n- Домашних заданиях\n- Контактах школы")

FAQ_ANSWERS = {
    "каникулы": "Ближайшие каникулы с 25 марта по 2 апреля",
    "собрание": "Следующее родительское собрание 5 апреля в 18:00",
    "расписание": "Чтобы узнать расписание, нажмите кнопку '📅 Расписание' и введите класс и день недели",
    "учитель": "Контакты учителей можно получить у классного руководителя",
    "домашнее задание": "Домашние задания публикуются в электронном дневнике",
    "кружки": "Список кружков и секций доступен на сайте школы"
}


@router.message(F.text == "ℹ️ FAQ")
async def faq_handler(message: Message):
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


    faq_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Когда каникулы?")],
            [KeyboardButton(text="Когда собрание?")],
            [KeyboardButton(text="Как узнать расписание?")],
            [KeyboardButton(text="Как связаться с учителем?")],
            [KeyboardButton(text="Где найти домашнее задание?")],
            [KeyboardButton(text="Какие есть кружки?")],
            [KeyboardButton(text="Другой вопрос")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        "Выберите вопрос из списка или задайте свой:",
        reply_markup=faq_keyboard
    )


@router.message(F.text.in_(FAQ_ANSWERS.keys()) |
                F.text.in_([q[:-1] for q in FAQ_ANSWERS.keys()]) |
                F.text.endswith("?"))
async def process_faq(message: Message):
    question = message.text.lower().replace("?", "").strip()
    answer = None

    for keyword, ans in FAQ_ANSWERS.items():
        if keyword in question:
            answer = ans
            break

    if not answer:
        answer = await chat_with_ai(message)

    await message.answer(answer, reply_markup=main_menu_keyboard)


@router.message(Command("admin"))
async def admin_start(message: Message, state: FSMContext):
    await message.answer("Введите пароль администратора:")
    await state.set_state(AdminStates.waiting_password)


@router.message(AdminStates.waiting_password)
async def check_admin_password(message: Message, state: FSMContext):
    if message.text == config.ADMIN_PASSWORD:
        await message.answer(
            "✅ Доступ разрешен. Используйте команды:\n/add_schedule - Добавить расписание\n/add_event - Добавить событие")
        await state.clear()
    else:
        await message.answer("❌ Неверный пароль")
        await state.clear()


@router.message(Command("add_schedule"))
async def add_schedule_start(message: Message, state: FSMContext):
    await message.answer("Введите данные в формате: Класс День Уроки\nПример: 7А Понедельник Математика,Физика,Химия")
    await state.set_state(AdminStates.waiting_schedule)


@router.message(AdminStates.waiting_schedule)
async def process_add_schedule(message: Message, state: FSMContext):
    try:
        class_name, day, lessons = message.text.split(maxsplit=2)
        async with db.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO schedule (class_name, day, lessons) VALUES ($1, $2, $3)",
                class_name, day, lessons
            )
        await message.answer("✅ Расписание добавлено!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        await state.clear()


@router.message(F.text)
async def process_question(message: Message):
    if len(message.text) > 3:
        lower_text = message.text.lower()
        if any(word in lower_text for word in ["каникул", "отдых"]):
            await message.answer("Ближайшие каникулы с 25 марта по 2 апреля")
        elif any(word in lower_text for word in ["собран", "встреч"]):
            events = await db.get_upcoming_events(30)
            if events:
                response = "Ближайшие события:\n" + "\n".join(
                    f"{e['event_name']} ({e['event_date']})" for e in events
                )
                await message.answer(response)
            else:
                await message.answer("Ближайших событий не найдено")
        else:
            response = await chat_with_ai(message)
            await message.answer(response)


async def send_reminders():
    events = await db.get_upcoming_events(1)
    for event in events:
        # Здесь нужно реализовать рассылку всем пользователям
        # Временно отправляем себе
        await bot.send_message(
            chat_id=config.ADMIN_CHAT_ID,
            text=f"🔔 Напоминание: {event['event_name']} завтра!\n{event['description']}"
        )


async def on_startup():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_reminders, 'cron', hour=9, minute=0)
    scheduler.start()


async def main():
    await db.create_pool()
    await on_startup()

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    try:
        await dp.start_polling(bot)
    finally:
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(main())