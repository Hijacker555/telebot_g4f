""" PostgreSQL """
import asyncpg


DB_HOST = "212.86.108.148"
DB_DATABASE = "telebot"
DB_USER = "myuser"
DB_PASS = "mypass"


async def create_db_pool():
    return await asyncpg.create_pool(
        user=DB_USER,
        password=DB_PASS,
        database=DB_DATABASE,
        host=DB_HOST
    )


async def create_tables(conn):
    """Создание таблицы authorized_users"""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS authorized_users (
        user_id INTEGER PRIMARY KEY,
        username VARCHAR(255) UNIQUE,
        first_name VARCHAR(255),
        last_name VARCHAR(255),
        phone_number VARCHAR(20)
    );
    """

    create_messages_table_query = """
    CREATE TABLE IF NOT EXISTS users_messages (
        id SERIAL PRIMARY KEY,
        time TIMESTAMP DEFAULT NOW(),
        user_id INTEGER REFERENCES authorized_users (user_id) ON DELETE CASCADE,
        request TEXT NOT NULL,
        response TEXT NOT NULL
    );
    """
    try:
        # Используем асинхронные методы для выполнения запросов
        await conn.execute(create_table_query)
        await conn.execute(create_messages_table_query)
        print("Таблицы 'authorized_users' и 'users_messages' созданы")
    except asyncpg.PostgresError as ex:
        print("Ошибка при создании таблиц:", ex)


async def add_user(connection, user_id, username, first_name, last_name, phone):
    # Code to add the user to the 'authorized_users' table
    try:
        # Используем асинхронный метод execute
        insert_query = """
        INSERT INTO authorized_users (user_id, username, first_name, last_name, phone_number)
        VALUES ($1, $2, $3, $4, $5) RETURNING user_id;
        """
        result = await connection.fetchrow(insert_query, user_id, username, first_name, last_name, phone)
        return result['user_id']
    except asyncpg.PostgresError as ex:
        print("Ошибка при добавлении пользователя в базу данных:", ex)
        return None


async def check_user(connection, user_id):
    """Check if a user exists in the database and return user_id if found"""
    try:
        # Используем асинхронный метод fetchrow
        query = "SELECT user_id FROM authorized_users WHERE user_id = $1"
        user_data = await connection.fetchrow(query, user_id)
        if user_data:
            # Возвращаем кортеж с логическим значением и user_id
            return True, user_data['user_id']
        else:
            return False, None  # Возвращаем False и None, если пользователь не найден
    except asyncpg.PostgresError as ex:
        print("Ошибка при проверке пользователя в базе данных:", ex)
        return False, None  # Возвращаем False и None в случае ошибки


async def check_auth_user(connection, phone):
    """Check if a user exists in the database and return user_id if found"""
    try:
        query = "SELECT id, phone_number FROM authorized_users WHERE phone_number = $1"
        user_data = await connection.fetchrow(query, phone)
        if user_data:
            return True, user_data[0], user_data[1]
        else:
            return False, None, None
    except asyncpg.PostgresError as ex:
        print("Ошибка при проверке пользователя в базе данных:", ex)
        return False, None, None


async def get_all_users(conn):
    """Вывод всех authorized_users из таблицы username"""
    select_query = "SELECT username, phone_number FROM authorized_users;"
    try:
        rows = await conn.fetch(select_query)
        users = [(row['username'], row['phone_number'] if row['phone_number']
                  is not None else 'None') for row in rows]
        return users
    except asyncpg.PostgresError as ex:
        error_message = "Ошибка при получении authorized_users из базы данных: %s", ex
        return error_message


async def save_message_to_db(connection, user_id, request, response):
    """
    Сохранение сообщения в базу данных.
    Параметры:
    - connection: соединение с базой данных
    - user_id: идентификатор пользователя
    - request: текст запроса пользователя
    - response: текст ответа бота
    """
    insert_query = """
    INSERT INTO users_messages (user_id, request, response)
    VALUES ($1, $2, $3);
    """
    try:
        await connection.execute(insert_query, user_id, request, response)
    except asyncpg.PostgresError as ex:
        print("Ошибка при сохранении сообщения:", ex)



async def update_phone_number(connection, user_id, phone_number):
    """ Update the phone number for an existing user """
    update_query = "UPDATE authorized_users SET phone_number = $1 WHERE id = $2;"
    try:
        await connection.execute(update_query, phone_number, user_id)
    except asyncpg.PostgresError as ex:
        print("Ошибка при обновлении номера телефона пользователя:", ex)
