from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
)
from aiogram import F, Router, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.cloud_manage import MailWevDAV

import datetime
import asyncio
import os
import secrets

from sql_method.sql import DataBase
from config import *

router = Router()
admin_id = int(admin_id)
stop_event = 0
user_file = {}
user_task = {}

login = mail_login
password = secret_pass

cloud = MailWevDAV(login, password)

# Папка для хранения загруженных файлов
DOWNLOADS_FOLDER = "downloads_images"
if not os.path.exists(DOWNLOADS_FOLDER):
    os.makedirs(DOWNLOADS_FOLDER)

db = DataBase("database.db")
bot = Bot(token=TOKEN)


class SendFiles(StatesGroup):
    wait_files = State()
    client_id = State()
    project_name = State()
    file_name = State()
    file_path = State()

class Token(StatesGroup):
    token_state = State()


async def reminders():
        count_days = 3
        while count_days > 0:
            projects = await db.remember()
            # print(projects)
            for project_name, client_id in projects:
                # print(client_id)
                # print(project_name)
                if count_days == 1:
                    await bot.send_message(
                        admin_id,
                        text=f"У клиента осталось дней на согласовние: {count_days}",
                    )
                await bot.send_message(
                    int(client_id),
                    f"Напоминание: проект {project_name} еще не согласован\n"
                    f"Осталось дней до конца срока согласования: {count_days}",
                )

            # await asyncio.sleep(86400)
            await asyncio.sleep(10)
            count_days -= 1
        if count_days == 0:
            await bot.send_message(int(client_id), text="Ваш срок согласования истек")


async def generate_path(base_path="/downloads") -> str:
    """Создаем путь по умолчанию"""
    today = datetime.datetime.now()
    return f"{base_path}/{today.year}/{today.month}/{today.day}"


async def check_directory(remote_path):
    """Проверяет наличие директории"""
    parts = remote_path.strip("/").split("/")
    current_path = ""

    for part in parts:
        current_path += f"/{part}"
        print(current_path)
        if not await cloud.check_dir(current_path):
            await cloud.create_dir(current_path)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    global stop_event
    stop_event = 0
    # if message.chat.username is None:
    #     username = 'none'
    # username = '@' + message.chat.username
    chat_id = message.chat.id
    # print(f'ID: {username}')
    # print(admin_id, type(admin_id))

    test = await cloud.test_connection()
    if test:
        await message.answer("Облако подключено")
    else:
        await message.answer("Ошибка подключения")
        return

    # Если пользователь админ -> выводим его проекты
    if chat_id == admin_id:
        projects = await db.get_projects(f"{chat_id}")
        print(projects)
        keyboard = InlineKeyboardBuilder()
        for project in projects:
            project_name = project[0]
            print(project_name)
            client = await db.take_client_id(project_name)
            if client:
                client_id = client[0]
            else:
                client_id = None
            print(client_id)
            button = InlineKeyboardButton(
                text=f"{project_name}",
                callback_data=f"selected_{project_name}_{client_id}",
            )
            # print(button)
            keyboard.add(button)
            keyboard.adjust(2)
        await message.answer("Выберите проект:", reply_markup=keyboard.as_markup())
    # Иначе выводим другое сообщение

    else:
        await message.answer(f"Добро пожаловать.\nВставьте токен который прислал вам исполнитель")
        await state.set_state(Token.token_state)


@router.message(Token.token_state)
async def take_token(message: Message, state: FSMContext):
    await state.update_data(token=message.text)
    token = message.text
    chat_id = message.chat.id
    client_name = message.from_user.full_name
    project = await db.take_project_name(token)
    project_name = project[0]
    if not len(token) == 32:
        await message.answer('Неверный токен!\nПроверьте токен еще раз')
        return
    else:
        await db.confirm_user(token, chat_id, client_name)
        await db.add_to_project(chat_id, token)
        await message.answer(f'Вы прикрелены к проекту: {project_name}')


@router.callback_query(lambda call: call.data.startswith("selected_"))
async def send_files(call: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(call.id)
    info = call.data.split("_")

    print(info[1], info[2])

    project_name = info[1]
    user_id = info[2]

    keyboard = InlineKeyboardBuilder()
    button = InlineKeyboardButton(text="Создать токен", callback_data=f"create_token_{project_name}")
    keyboard.add(button)
    keyboard.adjust(1)
    if user_id == "None":
        await call.message.answer(
            "В данном проекте отстсвует чат айди клиента.\n Отправьте ему токен для подключения к проекту",
            reply_markup=keyboard.as_markup(),
        )
        return

    await state.update_data(client_id=user_id, project_name=project_name)
    await state.set_state(SendFiles.wait_files)
    await call.message.answer(
        f"вы выбрали проект: {project_name}\n"
        f"Клиент: {user_id}\n"
        "Отправьте файлы которые хотите отправить клиенту"
    )

@router.callback_query(lambda call: call.data.startswith("create_token"))
async def create_token(call: CallbackQuery):
    project_name = call.data.split('_')[2]
    await bot.answer_callback_query(call.id)
    token = await generate_token()
    await db.add_token(project_name, token)
    await call.message.answer(f'Токен для присоединения к проекту:\n<code>{token}</code>', parse_mode="HTML")

@router.message(F.document | F.photo, SendFiles.wait_files)
async def take_documents(message: Message, state: FSMContext):
    data = await state.get_data()
    client_id = data["client_id"]
    project_name = data["project_name"]
    print(project_name)

    # Обработка файлов
    if client_id not in user_file:
        user_file[client_id] = []

    if message.document:
        file_name = message.document.file_name
        file_id = message.document.file_id
        print(f"document: {file_name}")
    if message.photo:
        await message.answer(
            "Бот принимает только файлы, попробуйте оптравить фотографию в виде файла\n"
            'уберите галочку "Сжать фотографию"'
        )
        return
    file = await bot.get_file(file_id)
    file_path = os.path.join(DOWNLOADS_FOLDER, file_name)
    print(f"Path file: {file_path}")

    await state.update_data(file_name=file_name)

    await bot.download_file(file.file_path, f".\\{file_path}")
    await message.answer(f"Файл {file_name} успешно загружен")

    user_file[client_id].append(file_name)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отправить клиенту",
                    callback_data=f"send_to_{client_id}_{project_name}",
                )
            ]
        ]
    )
    await message.answer(
        "Если вы загрузили все файлы нажмите на кнопку", reply_markup=keyboard
    )


@router.callback_query(lambda call: call.data.startswith("send_to_"))
async def send_files_to_client(call: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(call.id)
    client_id = call.data.split("_")[2]
    # print(call.data.split("_"))
    # print(f"\n\n{client_id}")
    # print(user_file)

    data = await state.get_data()
    file_name = data["file_name"]
    project_name = data["project_name"]
    print(file_name)

    if client_id not in user_file or not user_file[client_id]:
        await call.message.answer("Вы не загрузили файлы")
        return
    print(user_file[client_id][0])
    file_path = os.path.join(DOWNLOADS_FOLDER, file_name)
    if not os.path.exists(file_path):
        await call.message.answer(f"Файл {file_name} не найден")
        return
    try:
        await call.message.answer("Файлы отправлены")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Соглаосовать",
                        callback_data=f"access_{client_id}_{project_name}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Не согласовывать",
                        callback_data=f"rejection_{client_id}_{project_name}",
                    )
                ],
            ]
        )
        file = FSInputFile(file_path)
        await bot.send_document(chat_id=int(client_id), document=file)
        await bot.send_message(
            chat_id=int(client_id),
            text="Вам прислали файл для согласования его.\n"
            'Нажмите "Согласовать", если готовы согласовать, если нет, то нажмите "Нет"',
            reply_markup=keyboard,
        )
        await db.update_status("waiting", project_name)
    except Exception as e:
        print(f"{e}", f"{e.args}")
    await state.update_data(file_name=file_name)
    task = asyncio.create_task(reminders())
    user_task[client_id] = task


@router.callback_query(
    lambda call: call.data.startswith("access_") or call.data.startswith("rejection_")
)
async def access_project(call: CallbackQuery):
    # await bot.answer_callback_query(call.id)
    print(call.data)
    client_id = call.data.split("_")[1]
    project_name = call.data.split("_")[2]
    file_name = user_file.get(client_id, [None])[0]
    local_path = os.path.join(DOWNLOADS_FOLDER, file_name)
    status = call.data.split("_")[0]

    if status == "access":
        path = await generate_path()
        await check_directory(path)
        user_task[client_id].cancel()
        del user_task[client_id]
        await bot.send_message(admin_id, text="Пользователь согласовал проект")
        await cloud.upload_file(
            local_path=local_path, remote_path=path + f"/{file_name}"
        )
        await db.complete_project(project_name=project_name)

    if status == "rejection":
        user_task[client_id].cancel()
        del user_task[client_id]
        await bot.send_message(admin_id, text="Пользователь не согласовал проект")
        await bot.send_message(
            client_id,
            text="Для обсуждения вопрос по проетку перейдите по ссылке"
            "\nhttps://t.me/+If7bECoJg0I2OTgy",
        )
        await bot.send_message(admin_id, text="https://t.me/+If7bECoJg0I2OTgy")


# -----------------------------------------КЛИЕНТСКАЯ СТОРОНА БОТА------------------------------------------- #


async def generate_token() -> str:
    """generate unique token"""
    return secrets.token_hex(16)