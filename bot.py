import telebot
import requests
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import re
import mysql.connector
from config import telegram_bot_token as token
from config import db_name, db_username, db_password, host, auth_plugin

# connection to MySQL
def get_db_connection():
    return mysql.connector.connect(host=host,
                                database=db_name,
                                user=db_username,
                                password=db_password,
                                auth_plugin=auth_plugin)

connection = get_db_connection()
cursor=connection.cursor()
table = "sessions"

# empty storage for sessions
sessions = {}

# apply bot token
bot = telebot.TeleBot(token)

# start function
@bot.message_handler(commands=['start'])
def welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.InlineKeyboardButton("Registration ®️")
    btn2 = types.InlineKeyboardButton("Login 🔐")
    markup.add(btn1, btn2)
    bot.reply_to(message, "Welcome, if you have an account chose Login 🔐, if not - Registration ®️", reply_markup=markup)  

# registration
@bot.message_handler(regexp='Registration ®️')
def username_field(message):
    # Handle login name
    msg = bot.send_message(message.chat.id, text="Enter username for your session: ")
    bot.register_next_step_handler(msg, reg)

def reg(message):
    login = message.text.strip()

    if login == '':
        bot.send_message(message.chat.id, text="Username cannot be empty.")
        return
    
    # connection to MySQL
    connection = get_db_connection()
    cursor=connection.cursor()

    login = message.text
    
    enter = cursor.execute(f"SELECT login FROM {table} WHERE login = %s", (login,))

    if cursor.fetchone():
        bot.send_message(message.chat.id, text="This username is already taken.")
        cursor.close()
        connection.close()
        return
    
    # Handle password
    msg = bot.send_message(message.chat.id, text="Enter a password for this username: ")
    bot.register_next_step_handler(msg, register_user, login)
    
def register_user(message, login):
    password = message.text.strip()

    # Handle password
    if password == '':
        bot.send_message(message.chat.id, text="Password cannot be empty.")
        return

    connection = get_db_connection()
    cursor = connection.cursor()

    # Adding session
    cursor.execute(f"INSERT INTO {table} (login, password) VALUES (%s, %s)", (login, password,))
    connection.commit()
    cursor.close()
    connection.close()

    bot.send_message(message.chat.id, text="Registration successful ✅\nNow you can login into your session 🔓")

@bot.message_handler(regexp='Login 🔐')
# Handle login
def ask_login_username(message):
    msg = bot.send_message(message.chat.id, "Enter your username:")
    bot.register_next_step_handler(msg, ask_login_password)

def ask_login_password(message):
    login = message.text.strip()
    if login == '':
        bot.send_message(message.chat.id, "Username cannot be empty.")
        return
    msg = bot.send_message(message.chat.id, "Enter your password:")
    bot.register_next_step_handler(msg, login_user, login)



#
def login_user(message, login):
    password = message.text.strip()

    connection = get_db_connection()
    cursor = connection.cursor()

    enter = cursor.execute(f"SELECT id FROM {table} WHERE login = %s AND password = %s", (login, password,))
    row = cursor.fetchone()

    if row:
        session_id = row[0]
        sessions[message.chat.id] = session_id 
        markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Login successful! 🎉", reply_markup=markup)
        users_menu = build_users_inline_menu(session_id)
        bot.send_message(message.chat.id, "Choose an action:", reply_markup=users_menu)
    else:
        bot.send_message(message.chat.id, "Incorrect login or password ❌")

    cursor.close()
    connection.close()

# empty storage for new users
new_users = {}

# Inline menu for users
def build_users_inline_menu(session_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM users WHERE session_id = %s", (session_id,))
    users = cursor.fetchall()
    cursor.close()
    connection.close()

    markup = types.InlineKeyboardMarkup()
    
    # Adding new user
    add_btn = types.InlineKeyboardButton("➕ Add user", callback_data="add_user")
    markup.add(add_btn)

    # All of users
    for user in users:
        name = user[0]
        markup.add(types.InlineKeyboardButton(f"👤 {name}", callback_data=f"user_{name}"))

    return markup

# CallBack
@bot.callback_query_handler(func=lambda call: call.data == "add_user")
def handle_add_user_callback(call):
    session_id = sessions.get(call.message.chat.id)

    if not session_id:
        bot.send_message(call.message.chat.id, "You need to log in first.")
        return
    msg = bot.send_message(call.message.chat.id, "Enter username:")
    bot.register_next_step_handler(msg, ask_amount)

def ask_amount(message):
    chat_id = message.chat.id
    name = message.text.strip()

    if not name:
        bot.send_message(chat_id, "Username cannot be empty.")
        return
    new_users[chat_id] = {'name': name}
    msg = bot.send_message(chat_id, "Enter amount of expenses:")
    bot.register_next_step_handler(msg, ask_note)

def ask_note(message):
    chat_id = message.chat.id
    try:
        amount = int(message.text.strip())
    except ValueError:
        bot.send_message(chat_id, "The amount must be a number. Try again.")
        return
    new_users[chat_id]['amount'] = amount
    msg = bot.send_message(chat_id, "Enter a note on what the money was spent on:")
    bot.register_next_step_handler(msg, save_user_to_db)

# Saving into db
def save_user_to_db(message):
    chat_id = message.chat.id
    note = message.text.strip()

    user_data = new_users.get(chat_id)
    # print(user_data)
    if not user_data:
        bot.send_message(chat_id, "An error occurred. Please try again.")
        return

    user_data['note'] = note
    session_id = sessions.get(chat_id)

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("INSERT INTO users (session_id, name, amount, note) VALUES (%s, %s, %s, %s)", (session_id, user_data['name'], user_data['amount'], user_data['note']))
    connection.commit()
    cursor.close()
    connection.close()

    del new_users[chat_id]

    # Update menu of users
    updated_menu = build_users_inline_menu(session_id)
    bot.send_message(chat_id, f"User {user_data['name']} added successfully ✅")
    bot.send_message(chat_id, "Select an action or user:", reply_markup=updated_menu)


bot.polling()