import telebot
import requests
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import re
import mysql.connector
from config import telegram_bot_token as token
from db_worker import get_db_connection

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



# login in session
def login_user(message, login):
    password = message.text.strip()
    chat_id = message.chat.id

    connection = get_db_connection()
    cursor = connection.cursor()

    # Validate login
    cursor.execute(f"SELECT id FROM {table} WHERE login = %s AND password = %s", (login, password,))
    row = cursor.fetchone()

    if row:
        session_id = row[0]
        sessions[chat_id] = session_id

        # Remove keyboard
        markup = types.ReplyKeyboardRemove()
        bot.send_message(chat_id, "Login successful! 🎉", reply_markup=markup)

        # Check if user already exists for this chat_id
        cursor.execute("SELECT COUNT(*) FROM users WHERE session_id = %s AND chat_id = %s", (session_id, chat_id))
        exists = cursor.fetchone()[0]

        if exists == 0:
            # Determine name: Telegram username or fallback to login
            tg_name = message.from_user.username or login
            cursor.execute("INSERT INTO users (session_id, name, amount, note, chat_id) VALUES (%s, %s, %s, %s, %s)",
                           (session_id, tg_name, 0, '', chat_id))
            connection.commit()
            bot.send_message(chat_id, f"User '{tg_name}' created automatically for your session ✅")

        cursor.close()
        connection.close()

        # Show menu
        users_menu = build_users_inline_menu(session_id)
        bot.send_message(chat_id, "Choose an action:", reply_markup=users_menu)

    else:
        bot.send_message(chat_id, "Incorrect login or password ❌")
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

    # All of users
    for user in users:
        name = user[0]
        markup.add(types.InlineKeyboardButton(f"👤 {name}", callback_data=f"user_{name}"))

    markup.add(types.InlineKeyboardButton("🔒 Logout", callback_data="logout"))

    return markup

# # CallBack
# @bot.callback_query_handler(func=lambda call: call.data == "add_user")
# def handle_add_user_callback(call):
#     session_id = sessions.get(call.message.chat.id)

#     if not session_id:
#         bot.send_message(call.message.chat.id, "You need to log in first.")
#         return
#     msg = bot.send_message(call.message.chat.id, "Enter username:")
#     bot.register_next_step_handler(msg, ask_amount)

# def ask_amount(message):
#     chat_id = message.chat.id
#     name = message.text.strip()

#     if not name:
#         bot.send_message(chat_id, "Username cannot be empty.")
#         return 

#     session_id = sessions.get(chat_id)
#     if not session_id:
#         bot.send_message(chat_id, "You need to log in first.")
#         return

#     connection = get_db_connection()  
#     cursor = connection.cursor()   

#     cursor.execute("SELECT COUNT(*) FROM users WHERE session_id = %s AND chat_id = %s", (session_id, chat_id))
#     exists = cursor.fetchone()[0]

#     if exists:
#         bot.send_message(chat_id, "❌You already created a user in this session. You can't create more.")
#         return

#     cursor.execute("SELECT COUNT(*) FROM users WHERE session_id = %s AND name = %s", (session_id, name))
#     count = cursor.fetchone()[0]

#     if count > 0:
#         msg = bot.send_message(chat_id, f"A user with the name '{name}' already exists. Please choose another.")
#         bot.register_next_step_handler(msg, ask_amount)
#         return

#     new_users[chat_id] = {'name': name}
#     msg = bot.send_message(chat_id, "Enter amount of expenses:")
#     bot.register_next_step_handler(msg, ask_note)

#     cursor.close()
#     connection.close()


# def ask_note(message):
#     chat_id = message.chat.id
#     try:
#         amount = int(message.text.strip())
#     except ValueError:
#         bot.send_message(chat_id, "The amount must be a number. Try again.")
#         return
#     new_users[chat_id]['amount'] = amount
#     msg = bot.send_message(chat_id, "Enter a note on what the money was spent on:")
#     bot.register_next_step_handler(msg, save_user_to_db)

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

    cursor.execute("INSERT INTO users (session_id, name, amount, note, chat_id) VALUES (%s, %s, %s, %s, %s)", (session_id, user_data['name'], user_data['amount'], user_data['note'], chat_id))

    connection.commit()
    cursor.close()
    connection.close()

    del new_users[chat_id]

    # Update menu of users
    updated_menu = build_users_inline_menu(session_id)
    bot.send_message(chat_id, f"User {user_data['name']} added successfully ✅")
    bot.send_message(chat_id, "Select an action or user:", reply_markup=updated_menu)

@bot.callback_query_handler(func=lambda call: call.data.startswith("user_"))
def handle_user_click(call):
    session_id = sessions.get(call.message.chat.id)
    username = call.data.split("_", 1)[1]

    connection = get_db_connection()
    cursor = connection.cursor()

    # Get all expenses for this name in this session
    cursor.execute("SELECT amount, note FROM users WHERE session_id = %s AND name = %s", (session_id, username))
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    if not rows:
        bot.send_message(call.message.chat.id, f"{username} has no expenses yet.")
        return

    total = sum(row[0] for row in rows)
    notes = [row[1] for row in rows]
    note_text = ", ".join(notes)

    text = f"👤 {username}\n💸 Total Spent: {total}\n📝 Notes: {note_text}"

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("➕ Add Expense", callback_data=f"add_expense_{username}")
    )

    bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "logout")
def handle_logout(call):
    chat_id = call.message.chat.id

    if chat_id in sessions:
        del sessions[chat_id]

    bot.send_message(chat_id, "You have been logged out successfully. 🔒")
    
    # Show start menu again
    welcome(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_expense_"))
def add_expense_handler(call):
    username = call.data.split("_", 2)[2]
    chat_id = call.message.chat.id
    session_id = sessions.get(chat_id)

    # Verify that the selected user belongs to this chat ID
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT 1 FROM users WHERE session_id = %s AND name = %s AND chat_id = %s", (session_id, username, chat_id))
    is_authorized = cursor.fetchone()
    cursor.close()
    connection.close()

    if not is_authorized:
        bot.send_message(chat_id, "❌ You can only add expenses to your user.")
        return

    msg = bot.send_message(chat_id, f"Enter amount for {username}:")
    bot.register_next_step_handler(msg, ask_expense_note, username)


def ask_expense_note(message, username):
    chat_id = message.chat.id
    try:
        amount = int(message.text.strip())
    except ValueError:
        bot.send_message(chat_id, "Amount must be a number.")
        msg = bot.send_message(chat_id, f"Enter amount for {username}:")
        bot.register_next_step_handler(msg, ask_expense_note, username)
        return

    new_users[chat_id] = {"username": username, "amount": amount}
    msg = bot.send_message(chat_id, "Enter note for this expense:")
    bot.register_next_step_handler(msg, save_expense_record)

def save_expense_record(message):
    chat_id = message.chat.id
    note = message.text.strip()
    data = new_users.get(chat_id)

    if not data:
        bot.send_message(chat_id, "Something went wrong. Try again.")
        return

    session_id = sessions.get(chat_id)
    username = data["username"]
    amount = data["amount"]

    connection = get_db_connection()
    cursor = connection.cursor()

    # User record
    cursor.execute("SELECT amount, note FROM users WHERE session_id = %s AND name = %s", (session_id, username))
    row = cursor.fetchone()

    if row:
        # Update existing user's total amount and append note
        old_amount, old_note = row
        new_amount = old_amount + amount
        new_note = (old_note or '') + ", " + note

        cursor.execute("UPDATE users SET amount = %s, note = %s WHERE session_id = %s AND name = %s",
                       (new_amount, new_note, session_id, username))
    else:
        cursor.execute("INSERT INTO users (session_id, name, amount, note) VALUES (%s, %s, %s, %s)",
                       (session_id, username, amount, note))

    connection.commit()
    cursor.close()
    connection.close()

    del new_users[chat_id]
    bot.send_message(chat_id, f"Added {amount} to {username} ✅")
    updated_menu = build_users_inline_menu(session_id)
    bot.send_message(chat_id, "Select an action or user:", reply_markup=updated_menu)

# start bot
bot.polling()