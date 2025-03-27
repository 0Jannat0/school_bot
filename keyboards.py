from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Расписание")],
        [KeyboardButton(text="📌 События")],
        [KeyboardButton(text="ℹ️ FAQ")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)