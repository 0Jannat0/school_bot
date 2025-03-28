import config
import os
from aiogram.types import Message
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
async def chat_with_ai(message: Message):
    try:


        client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
                )

        completion = client.chat.completions.create(
            model="google/gemma-3-1b-it:free",
            temperature=0.7,
            messages=[{
            "role": "system",
                "content": "Ты школьный ассистент, который "
            }, {
                "role": "user",
                "content": message.text
                }],
        )
        reply_text = completion.choices[0].message.content
        await message.answer(reply_text)
    except Exception as e:
        print(f"AI Error: {e}")
        return "Не могу получить ответ. Попробуйте позже."