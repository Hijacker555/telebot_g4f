#!/usr/bin/env python

import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (Application, CommandHandler, 
                        MessageHandler, filters, CallbackContext, ContextTypes)
import asyncio
import g4f
from contextlib import asynccontextmanager
from db import *
import nest_asyncio


nest_asyncio.apply()

# Конфигурация логирования
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Провайдеры
_providers = [g4f.Provider.Bing,
              g4f.Provider.GeekGpt,
              g4f.Provider.GptChatly,
              g4f.Provider.Liaobots,
              g4f.Provider.Phind,
              g4f.Provider.Raycast]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    async with database_connection(context.bot_data['db_pool']) as connection:
        await create_tables(connection)
        user_exists = await check_user(connection, update.effective_user.id)
        if user_exists: 
            await update.message.reply_text(
                "Вы уже авторизованы. Чем могу помочь?",
                reply_markup=ReplyKeyboardRemove(),  # Убираем клавиатуру
            )
        else:
            reply_keyboard = [[KeyboardButton("🕵️ Авторизация", request_contact=True)]]
            await update.message.reply_text(
                "Пожалуйста, авторизуйтесь!",
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True, resize_keyboard=True
                ),
            )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact = update.effective_message.contact
    if contact:
        async with database_connection(context.bot_data['db_pool']) as connection:
            username = update.effective_user.username
            phone_number = contact.phone_number
            first_name = contact.first_name
            last_name = contact.last_name
            user_id = update.effective_user.id

            # Добавляем пользователя в базу данных
            await add_user(connection, user_id, username, first_name, last_name, phone_number)

            await update.message.reply_text(text="Спасибо! Чем я сегодня могу Вам помочь?")


async def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text
    user_id = update.effective_user.id

    # Выбор провайдера для обработки запроса
    # Пример: используем первый провайдер из списка _providers
    provider_response = await run_provider(_providers[1], user_message)

    # Отправляем ответ пользователю
    await update.message.reply_text(provider_response)

    # Запись сообщения в базу данных
    async with database_connection(context.bot_data['db_pool']) as connection:
        await save_message_to_db(connection, user_id, user_message, provider_response)



async def run_provider(provider: g4f.Provider.BaseProvider, user_input: str):
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.default,
            messages=[{"role": "user", "content": user_input}],
            provider=provider,
        )
        return f"{response}"
    except Exception as e:
        return f"{provider.__name__}: Error - {e}"


@asynccontextmanager
async def database_connection(pool):
    async with pool.acquire() as connection:
        yield connection

async def init_db_pool():
    db_pool = await create_db_pool()
    return db_pool



async def main() -> None:
    """Run the bot."""
    application = Application.builder().token("6723546111:AAGKqD7uw2BCtX5oo1iFuTqB6qbRRrv4Oc0").build()
    
    # Добавляем обработчики
    start_handler = CommandHandler("start", start)
    contact_handler = MessageHandler(filters._Contact(), handle_contact)  # Убедитесь, что используете filters.Contact() после обновления библиотеки
    text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)

    application.add_handler(start_handler)
    application.add_handler(contact_handler)
    application.add_handler(text_handler)

    # Инициализация пула соединений с базой данных
    db_pool = await init_db_pool()
    application.bot_data['db_pool'] = db_pool

    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())