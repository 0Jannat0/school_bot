import asyncpg
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD

pool = None

async def create_pool():
    global pool
    pool = await asyncpg.create_pool(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    print("✅ Подключение к БД установлено")


async def close_pool():
    global pool
    if pool:
        await pool.close()
        print("✅ Подключение к БД закрыто")


# async def get_schedule(class_name: str, day: str):
#     class_name = class_name.strip()
#     day = day.strip()
#
#     async with pool.acquire() as conn:
#         print(f"Запрос в БД: класс - {class_name}, день - {day}")
#         row = await conn.fetchrow(
#             "SELECT lessons FROM schedule WHERE class_name = $1 AND day = $2",
#             class_name, day
#         )
#         if row:
#             print(f"Найдено расписание: {row['lessons']}")
#         else:
#             print("Расписание не найдено.")
#         return row["lessons"] if row else None

async def get_schedule(class_name: str, day: str):
    class_name = class_name.strip().replace('A', 'А')
    day = day.strip()

    async with pool.acquire() as conn:
        print(f"Запрос в БД: класс - {class_name}, день - {day}")
        row = await conn.fetchrow(
            "SELECT lessons FROM schedule WHERE class_name = $1 AND day = $2",
            class_name, day
        )
        if row:
            print(f"Найдено расписание: {row['lessons']}")
        else:
            print("Расписание не найдено.")
        return row["lessons"] if row else None


async def get_events():
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT event_name, event_date, description FROM events ORDER BY event_date ASC")
        return [{"event_name": row["event_name"], "event_date": row["event_date"], "description": row["description"]} for row in rows]

async def check_user(user_id: int):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT id FROM users WHERE user_id = $1", user_id)

async def add_user(user_id: int, username: str, first_name: str, last_name: str):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (user_id, username, first_name, last_name) VALUES ($1, $2, $3, $4)",
            user_id, username, first_name, last_name
        )
async def get_events():
    async with pool.acquire() as conn:
        try:
            rows = await conn.fetch("""
                SELECT event_name, event_date, description 
                FROM events
                ORDER BY event_date ASC
            """)
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Ошибка при получении событий: {e}")
            return None

async def get_upcoming_events(days: int):
    async with pool.acquire() as conn:
        try:
            return await conn.fetch(
                """
                SELECT event_name, event_date::date, description 
                FROM events 
                WHERE event_date BETWEEN CURRENT_DATE AND CURRENT_DATE + $1 * INTERVAL '1 day'
                ORDER BY event_date
                """,
                days
            )
        except Exception as e:
            print(f"Ошибка при получении событий: {e}")
            return None