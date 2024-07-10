from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import json
import asyncio

from aiogram.types import ReplyKeyboardRemove
from aiogram.types.web_app_info import WebAppInfo
from dotenv import load_dotenv
import os
from aiogram import types
from aiogram import executor
import sqlite3 as sq

load_dotenv()
bot = Bot(token=os.getenv('TOKEN_BOT'))
dp = Dispatcher(bot, storage=MemoryStorage())

ADMIN_CHAT_ID = "5521511837"

base = sq.connect('data.db')
cur = base.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS files(file_id TEXT PRIMARY KEY, user_id INTEGER)")
base.commit()


@dp.message_handler(commands="start")
async def start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("открыть форму запроса",
                                    web_app=WebAppInfo(
                                        url=f"https://perevyazko1.github.io/bot-acc-front")))
    await message.answer(f'Привет {message.from_user.first_name} для отправки формы нажми на кнопку 👇',
                         reply_markup=markup)


@dp.message_handler(commands="send_form")
async def send_form(message: types.Message):
    await message.answer("Отправь фото или скрин товара.")


@dp.message_handler(content_types=['web_app_data'])
async def web_app(message: types.Message):
    data_form = json.loads(message.web_app_data.data)
    print(data_form)
    send_form_text = (f"Бренд: {data_form['brand']} \n\n"
                      f"Имя сотрудника  {data_form['name']} \n\n"
                      f"Магазин: {data_form['store']} \n\n"
                      f"Ссылка на товар : {data_form['reference']}\n\n"
                      f"О товаре:\n\n {data_form['about']} ")
    # Пересылаем изображение админу
    if data_form['photo'] != "":
        await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=data_form['photo'], caption=send_form_text)
    else:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=send_form_text)
    sent_message = await message.answer("Форма успешно отправлена в случае необходимости с тобой свяжутся")
    await asyncio.sleep(10)
    await bot.delete_message(chat_id=message.chat.id, message_id=sent_message.message_id)


@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    photo_id = message.photo[-1].file_unique_id  # Получаем file_id самой крупной версии изображения

    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cur.execute("INSERT INTO files (file_id, user_id) VALUES (?, ?)", (photo_id, user_id))
    base.commit()
    markup.add(types.KeyboardButton("открыть форму запроса",
                                    web_app=WebAppInfo(
                                        url=f"https://perevyazko1.github.io/bot-acc-front#{photo_id}")))
    sent_message = await message.answer(f'Отлично! Теперь нажми кнопку для заполнения формы 👇',
                                        reply_markup=markup)
    await asyncio.sleep(10)
    await bot.delete_message(chat_id=message.chat.id, message_id=sent_message.message_id)

    # Отправляем подтверждение пользователю

    # Здесь можно добавить логику для обработки открытия формы


@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def reply_to_user(message: types.Message):
    if message.reply_to_message:

        # Получаем ID пользователя из текста оригинального сообщения
        print(message)
        photo = message.reply_to_message.photo[3]
        photo_id = photo['file_unique_id']
        cur.execute("SELECT user_id FROM files WHERE file_id = ?", (photo_id,))
        result = cur.fetchone()
        user_id = result[0]

        admin_message = message.text

        # Отправляем ответ пользователю
        await bot.send_message(user_id, f"Ответ от администратора:\n{admin_message}")
    else:
        await message.reply("Пожалуйста, ответьте на сообщение пользователя.")


#

if __name__ == '__main__':
    executor.start_polling(dp)
