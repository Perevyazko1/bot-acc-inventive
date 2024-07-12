from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import json
import asyncio

from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.web_app_info import WebAppInfo
from dotenv import load_dotenv
import os
from aiogram import types
from aiogram import executor
import sqlite3 as sq
import re

load_dotenv()
bot = Bot(token=os.getenv('TOKEN_BOT'))
dp = Dispatcher(bot, storage=MemoryStorage())

# ADMIN_CHAT_ID = "5521511837"
# ADMIN_CHAT_ID = "674501380"
ADMIN_CHAT_ID = "-4244628531"

base = sq.connect('data.db')
cur = base.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS files(message_id TEXT PRIMARY KEY, user_id INTEGER, photo_id TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS admins(user_id INTEGER PRIMARY KEY, brand TEXT )")
base.commit()


@dp.message_handler(commands="start")
async def start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("открыть форму запроса",
                                    web_app=WebAppInfo(
                                        url=f"https://perevyazko1.github.io/bot-acc-front")))
    await message.answer(f'Привет {message.from_user.first_name} для отправки формы нажми на кнопку 👇',
                         reply_markup=markup)


@dp.message_handler(commands="registration_admin")
async def registration_admin(message: types.Message):
    restore = types.InlineKeyboardButton("restore", callback_data=f"restore")
    xiaomi = types.InlineKeyboardButton("xiaomi", callback_data=f"xiaomi")
    samsung = types.InlineKeyboardButton("samsung", callback_data=f"samsung")

    # Создание разметки с двумя кнопками в одном ряду
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(restore, xiaomi, samsung)

    await message.answer(
        f"Выбери Брэнд за который ты будешь отвечать. ",
        reply_markup=markup
    )


@dp.callback_query_handler(lambda c: c.data in ['restore', 'xiaomi', 'samsung'])
async def process_callback(callback_query: types.CallbackQuery):
    # Получаем данные из callback_query
    brand = callback_query.data
    user_id = callback_query.from_user.id
    print(brand, user_id)
    cur.execute("INSERT INTO admins (user_id, brand) VALUES (?, ?)", (user_id, brand))
    base.commit()

    # Отправляем ответ пользователю
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, f"Вы зарегистрированы админом в брэнде: {brand}")
    await bot.delete_message(chat_id=callback_query.message.chat.id,
                             message_id=callback_query.message.message_id)


@dp.message_handler(commands="send_form")
async def send_form(message: types.Message):
    await message.answer("Отправь фото или скрин товара.")


@dp.message_handler(content_types=['web_app_data'])
async def web_app(message: types.Message):
    data_form = json.loads(message.web_app_data.data)
    print(data_form)

    send_form_text = (
        f"Бренд: {data_form['brand']} \n\n"
        f"Имя сотрудника  {data_form['name']} \n\n"
        f"Магазин: {data_form['store']} \n\n"
        f"Ссылка на товар : {data_form['reference']}\n\n"
        f"О товаре:\n\n {data_form['about']} ")
    # Пересылаем изображение админу
    # await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=data_form['photo'], caption=send_form_text)

    if data_form['user_id'] != "":
        user_id = data_form['user_id']
        photo_id = data_form['photo']
        message = await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=data_form['photo'], caption=send_form_text)
        cur.execute("INSERT INTO files (message_id, user_id, photo_id) VALUES (?, ?, ?)",
                    (message.message_id, user_id, photo_id))
        base.commit()

        sent_message = await bot.send_message(chat_id=user_id,
                                              text="Форма успешно отправлена в случае необходимости с тобой свяжутся")
        # await asyncio.sleep(10)
        # await bot.delete_message(chat_id=message.chat.id, message_id=sent_message.message_id)


    else:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=send_form_text)


@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    photo_id = message.photo[-1].file_id  # Получаем file_id самой крупной версии изображения

    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("открыть форму запроса",
                                    web_app=WebAppInfo(
                                        url=f"https://perevyazko1.github.io/bot-acc-front#{user_id}/{photo_id}")))
    sent_message = await message.answer(f'Отлично! Теперь нажми кнопку для заполнения формы 👇',
                                        reply_markup=markup)
    await asyncio.sleep(10)
    await bot.delete_message(chat_id=message.chat.id, message_id=sent_message.message_id)

    # Отправляем подтверждение пользователю

    # Здесь можно добавить логику для обработки открытия формы


@dp.message_handler(content_types=types.ContentType.VIDEO)
async def handle_video(message: types.Message):
    if message.reply_to_message and message.reply_to_message.text is not None:
        ADMIN_CHAT_ID = "-4244628531"

        match = re.search(r'id\((\d+)\)', message.reply_to_message.text)
        print("test",message)

        admin_message = message.caption
        if match is None:
            video_id = message.video.file_id  # Получаем file_id самой крупной версии видео
            print(video_id)

            user_id = message.from_user.id

            await bot.send_video(chat_id=ADMIN_CHAT_ID, video=video_id,
                                 caption=f"Ответ от id({message.from_user.id}) {message.from_user.first_name}:\n{admin_message}")

        elif match:
            video_id = message.video.file_id
            await bot.send_video(chat_id=match.group(1), video=video_id,
                                 caption=f"Ответ от администратора :\n{admin_message}")

    elif message.reply_to_message and message.reply_to_message.text is None:

        current_message = message.reply_to_message.message_id
        cur.execute("SELECT user_id FROM files WHERE message_id = ?", (current_message,))
        result = cur.fetchone()
        admin_message = message.text
        print(message.reply_to_message.text)
        # Отправляем ответ пользователю
        if result:
            user_id = result[0]
            await bot.send_message(user_id, f"Ответ от администратора:\n{admin_message}")
    elif message.reply_to_message is None:
        await message.answer("Для отправки сообщения, нужно выбрать кому ответить")


@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def reply_to_user(message: types.Message):
    print("test",message)
    if message.reply_to_message and message.reply_to_message.text is not None:
        ADMIN_CHAT_ID = "-4244628531"

        match = re.search(r'id\((\d+)\)', message.reply_to_message.text)
        # print("test", match, message.reply_to_message.text, message)

        admin_message = message.text
        if match is None:

            await bot.send_message(ADMIN_CHAT_ID,
                                   f"Ответ от id({message.from_user.id}) {message.from_user.first_name}:\n{admin_message}")
        elif match:
            await bot.send_message(match.group(1), f"Ответ от администратора :\n{admin_message}")

    elif message.reply_to_message.caption is not None:
        match = re.search(r'id\((\d+)\)', message.reply_to_message.caption)
        admin_message = message.text
        ADMIN_CHAT_ID = "-4244628531"

        if match is None:
            await bot.send_message(ADMIN_CHAT_ID,
                                   f"Ответ от id({message.from_user.id}) {message.from_user.first_name}:\n{admin_message}")
        elif match:
            await bot.send_message(match.group(1), f"Ответ от администратора :\n{admin_message}")



    elif message.reply_to_message and message.reply_to_message.text is None:
        current_message = message.reply_to_message.message_id
        cur.execute("SELECT user_id FROM files WHERE message_id = ?", (current_message,))
        result = cur.fetchone()
        admin_message = message.text
        print(message.reply_to_message.text)
        # Отправляем ответ пользователю
        if result:
            user_id = result[0]
            await bot.send_message(user_id, f"Ответ от администратора:\n{admin_message}")
    elif message.reply_to_message is None:
        await message.answer("Для отправки сообщения, нужно выбрать кому ответить")


#

if __name__ == '__main__':
    executor.start_polling(dp)
