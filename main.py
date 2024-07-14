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
# ADMIN_CHAT_ID_Samsung = "-4244628531"
# ADMIN_CHAT_ID_RE_STORE = "-4200438125"
# ADMIN_CHAT_ID_XIAOMI = "-4211717137"

BRANDS = {
    "restore":
        "-4200438125",
    "samsung":
        "-4244628531",
    "xiaomi":
        "-4211717137"
}

base = sq.connect('data.db')
cur = base.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS files(message_id TEXT PRIMARY KEY, user_id INTEGER, photo_id TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS admins(user_id INTEGER PRIMARY KEY, brand TEXT )")
cur.execute("CREATE TABLE IF NOT EXISTS curent_chat(user_id INTEGER PRIMARY KEY, chat TEXT )")
base.commit()


@dp.message_handler(commands="start")
async def start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("открыть форму запроса",
                                    web_app=WebAppInfo(
                                        url=f"https://perevyazko1.github.io/bot-acc-front")))
    await message.answer(f'Привет {message.from_user.first_name} для отправки формы нажми на кнопку 👇',
                         reply_markup=markup)
@dp.message_handler(commands="info")
async def start(message: types.Message):
    await message.answer(f'🤖 Бот ассистент предназначен для предложения добавления новых аксессуаров, в ассортиментную матрицу re:store, xiaomi, samsung.\n\n'
f'Для отправки карточки, выбери в меню команду "Предложить аксессуар" \n\n'

"👤 Создатель: Андрей Перевязко\n\n"
"📲 TG: @perevyazko1"
                         )
@dp.callback_query_handler(lambda c: c.data in ['restore', 'xiaomi', 'samsung'])
async def process_callback(callback_query: types.CallbackQuery):
    # Получаем данные из callback_query
    brand = callback_query.data
    user_id = callback_query.from_user.id
    cur.execute("INSERT INTO admins (user_id, brand) VALUES (?, ?)", (user_id, brand))
    base.commit()

    # Отправляем ответ пользователю
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, f"Вы зарегистрированы админом в брэнде: {brand}")
    await bot.delete_message(chat_id=callback_query.message.chat.id,
                             message_id=callback_query.message.message_id)


@dp.message_handler(commands="send_form")
async def send_form(message: types.Message):
    user_id = message.from_user.id
    cur.execute("DELETE  FROM curent_chat WHERE user_id = ?", (user_id,))
    base.commit()
    await message.answer("Отправь фото или скрин товара.")


@dp.message_handler(content_types=['web_app_data'])
async def web_app(message: types.Message):
    data_form = json.loads(message.web_app_data.data)

    send_form_text = (
        f"Бренд: {data_form['brand']} \n\n"
        f"Имя сотрудника  {data_form['name']} \n\n"
        f"Магазин: {data_form['store']} \n\n"
        f"Ссылка на товар : {data_form['reference']}\n\n"
        f"О товаре:\n\n {data_form['about']} ")
    # Пересылаем изображение админу

    if data_form['user_id'] != "":
        user_id = data_form['user_id']
        photo_id = data_form['photo']
        message = await bot.send_photo(chat_id=data_form['chat_group_id'], photo=data_form['photo'],
                                       caption=send_form_text)
        cur.execute("INSERT INTO files (message_id, user_id, photo_id) VALUES (?, ?, ?)",
                    (message.message_id, user_id, photo_id))
        cur.execute("INSERT OR REPLACE INTO curent_chat (user_id, chat) VALUES (?, ?)",
                    (user_id, data_form['chat_group_id']))

        base.commit()

        sent_message = await bot.send_message(chat_id=user_id,
                                              text="Форма успешно отправлена в случае необходимости с тобой свяжутся")
        # await asyncio.sleep(10)
        # await bot.delete_message(chat_id=message.chat.id, message_id=sent_message.message_id)


    else:
        await bot.send_message(chat_id=data_form['chat_group_id'], text=send_form_text)


# -------------Защита от свободных фото в чате, так как они никому не придут--------------
@dp.message_handler(content_types=types.ContentTypes.PHOTO, is_reply=False,
                    chat_id=[BRANDS.get("xiaomi"), BRANDS.get("samsung"), BRANDS.get("restore")],
                    )
async def photo_in_chat_admins(message: types.Message):
    await message.answer("Чтобы выслать фото, нужно ответить на его сообщение")


# -------------Пересылка фото продавцу--------------
@dp.message_handler(content_types=types.ContentTypes.PHOTO, is_reply=True,
                    chat_id=[BRANDS.get("xiaomi"), BRANDS.get("samsung"), BRANDS.get("restore")],
                    )
async def reply_to_user(message: types.Message):
    if message.from_user.id == message.reply_to_message.from_user.id:
        await message.answer("Вы ответили на свое сообщение, чтобы отправить ответ, нужно ответить на сообщение "
                             "пользователя")

    if message.reply_to_message.text:
        match = re.search(r'id\((\d+)\)', message.reply_to_message.text)
        admin_message = message.text
        photo_id = message.photo[-1].file_id  # Получаем file_id самой крупной версии фото
        if match:
            await bot.send_photo(chat_id=match.group(1), photo=photo_id,
                                 caption=f"Фото от администратора: {message.chat.title}\n{admin_message}")
        else:
            await message.answer("Сообщение не доставлено.")
    elif message.reply_to_message.caption:
        match = re.search(r'id\((\d+)\)', message.reply_to_message.caption)
        admin_message = message.text
        photo_id = message.photo[-1].file_id  # Получаем file_id самой крупной версии фото
        if match:
            await bot.send_photo(chat_id=match.group(1), photo=photo_id,
                                 caption=f"Фото от администратора: {message.chat.title}\n{admin_message}")
        else:
            current_message = message.reply_to_message.message_id
            cur.execute("SELECT user_id FROM files WHERE message_id = ?", (current_message,))
            result = cur.fetchone()
            admin_message = message.text
            # Отправляем ответ пользователю
            if result:
                user_id = result[0]
                await bot.send_photo(chat_id=user_id, photo=photo_id,
                                     caption=f"Видео от администратора: {message.chat.title}\n{admin_message}")
            elif result is None:
                await message.answer("Сообщение не доставлено.")


# -------------Пересылка фото менеджерам--------------
@dp.message_handler(content_types=types.ContentTypes.PHOTO)
async def reply_to_manager(message: types.Message):
    user_id = message.from_user.id
    cur.execute("SELECT chat FROM curent_chat WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    user_message = message.text
    if result:
        current_chat = result[0]
        photo_id = message.photo[-1].file_id  # Получаем file_id самой крупной версии фото
        await bot.send_photo(chat_id=current_chat, photo=photo_id,
                             caption=f"Фото от id({message.from_user.id}) {message.from_user.first_name}:\n{user_message}")
    elif result is None:
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

    else:
        await message.answer("Чтобы общаться с админом, нужно сначала выслать карточку товара.")


# -------------Защита от свободных видео в чате, так как они никому не придут--------------
@dp.message_handler(content_types=types.ContentTypes.VIDEO, is_reply=False,
                    chat_id=[BRANDS.get("xiaomi"), BRANDS.get("samsung"), BRANDS.get("restore")],
                    )
async def video_in_chat_admins(message: types.Message):
    await message.answer("Чтобы выслать видео, нужно ответить на его сообщение")


# -------------Пересылка видео продавцу--------------
@dp.message_handler(content_types=types.ContentTypes.VIDEO, is_reply=True,
                    chat_id=[BRANDS.get("xiaomi"), BRANDS.get("samsung"), BRANDS.get("restore")],
                    )
async def reply_to_user(message: types.Message):
    if message.from_user.id == message.reply_to_message.from_user.id:
        await message.answer("Вы ответили на свое сообщение, чтобы отправить ответ, нужно ответить на сообщение "
                             "пользователя")

    if message.reply_to_message.text:
        match = re.search(r'id\((\d+)\)', message.reply_to_message.text)
        admin_message = message.text
        video_id = message.video.file_id  # Получаем file_id самой крупной версии видео
        if match:
            await bot.send_video(chat_id=match.group(1), video=video_id,
                                 caption=f"Видео от администратора: {message.chat.title}\n{admin_message}")
        else:
            await message.answer("Сообщение не доставлено.")
    elif message.reply_to_message.caption:
        match = re.search(r'id\((\d+)\)', message.reply_to_message.caption)
        admin_message = message.text
        video_id = message.video.file_id  # Получаем file_id самой крупной версии видео
        if match:
            await bot.send_video(chat_id=match.group(1), video=video_id,
                                 caption=f"Видео от администратора: {message.chat.title}\n{admin_message}")
        else:
            current_message = message.reply_to_message.message_id
            cur.execute("SELECT user_id FROM files WHERE message_id = ?", (current_message,))
            result = cur.fetchone()
            admin_message = message.text
            # Отправляем ответ пользователю
            if result:
                user_id = result[0]
                await bot.send_video(chat_id=user_id, video=video_id,
                                     caption=f"Видео от администратора: {message.chat.title}\n{admin_message}")
            elif result is None:
                await message.answer("Сообщение не доставлено.")


# -------------Пересылка видео менеджерам--------------
@dp.message_handler(content_types=types.ContentTypes.VIDEO)
async def reply_to_manager(message: types.Message):
    user_id = message.from_user.id
    cur.execute("SELECT chat FROM curent_chat WHERE user_id = ?", (user_id,))
    result = cur.fetchone()

    user_message = message.text
    if result:
        current_chat = result[0]
        video_id = message.video.file_id  # Получаем file_id самой крупной версии видео
        await bot.send_video(chat_id=current_chat, video=video_id,
                             caption=f"Видео от id({message.from_user.id}) {message.from_user.first_name}:\n{user_message}")
    else:
        await message.answer("Чтобы общаться с админом, нужно сначала выслать карточку товара.")


# -------------Защита от свободных сообщений в чате, так как они никому не придут--------------
@dp.message_handler(content_types=types.ContentTypes.TEXT, is_reply=False,
                    chat_id=[BRANDS.get("xiaomi"), BRANDS.get("samsung"), BRANDS.get("restore")],
                    )
async def message_in_chat_admins(message: types.Message):
    await message.answer("Чтобы ответить пользователю, нужно ответить на его сообщение")


# -------------Пересылка сообщений продавцу--------------
@dp.message_handler(content_types=types.ContentTypes.TEXT, is_reply=True,
                    chat_id=[BRANDS.get("xiaomi"), BRANDS.get("samsung"), BRANDS.get("restore")],
                    )
async def reply_to_user(message: types.Message):
    if message.from_user.id == message.reply_to_message.from_user.id:
        await message.answer("Вы ответили на свое сообщение, чтобы отправить ответ, нужно ответить на сообщение "
                             "пользователя")

    if message.reply_to_message.text:
        match = re.search(r'id\((\d+)\)', message.reply_to_message.text)
        admin_message = message.text
        if match:
            await bot.send_message(match.group(1), f"Ответ от администратора: {message.chat.title}\n{admin_message}")
        else:
            await message.answer("Сообщение не доставлено.")
    # проверка, что это не сообщение а фото или видео
    elif message.reply_to_message.caption:
        match = re.search(r'id\((\d+)\)', message.reply_to_message.caption)
        admin_message = message.text
        if match:
            await bot.send_message(match.group(1), f"Ответ от администратора: {message.chat.title}\n{admin_message}")
        else:
            current_message = message.reply_to_message.message_id
            cur.execute("SELECT user_id FROM files WHERE message_id = ?", (current_message,))
            result = cur.fetchone()
            admin_message = message.text
            # Отправляем ответ пользователю
            if result:
                user_id = result[0]
                await bot.send_message(user_id, f"Ответ от администратора: {message.chat.title}\n{admin_message}")
            elif result is None:
                await message.answer("Сообщение не доставлено.")


# -------------Пересылка сообщений менеджерам--------------
@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def reply_to_manager(message: types.Message):
    user_id = message.from_user.id
    print(message.chat.id)
    cur.execute("SELECT chat FROM curent_chat WHERE user_id = ?", (user_id,))
    result = cur.fetchone()

    user_message = message.text
    if result:
        current_chat = result[0]
        await bot.send_message(current_chat,
                               f"Сообщение от id({message.from_user.id}) {message.from_user.first_name}:\n{user_message}")
    else:
        await message.answer("Чтобы общаться с админом, нужно сначала выслать карточку товара.")


if __name__ == '__main__':
    executor.start_polling(dp)
