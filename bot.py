import telebot
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import types
import re
import mysql.connector
from config import telegram_bot_token as token
from config import db_name, db_username, db_password, host, auth_plugin

# connection to MySQL
connection = mysql.connector.connect(host=host,
                                    database=db_name,
                                    user=db_username,
                                    password=db_password,
                                    auth_plugin=auth_plugin)

cursor=connection.cursor()
table = "table_name"

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
def send_welcome(message):
    # Handle login
    msg = bot.send_message(message.chat.id, text="Enter username for your session: ")
    bot.register_next_step_handler(msg, reg)

def reg(message):
    login = message.text.strip()

    if login == '':
        bot.send_message(message.chat.id, text="Username cannot be empty.")
        return
    
    # connection to MySQL
    connection = mysql.connector.connect(host=host,
                                    database=db_name,
                                    user=db_username,
                                    password=db_password,
                                    auth_plugin=auth_plugin)

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

    if password == '':
        bot.send_message(message.chat.id, text="Password cannot be empty.")
        return

    connection = mysql.connector.connect(host=host,
                                    database=db_name,
                                    user=db_username,
                                    password=db_password,
                                    auth_plugin=auth_plugin)
    cursor = connection.cursor()

    # Вставка користувача
    cursor.execute(f"INSERT INTO {table} (login, password) VALUES (%s, %s)", (login, password,))
    connection.commit()
    cursor.close()
    connection.close()

    bot.send_message(message.chat.id, text="Registration successful ✅")

bot.polling()