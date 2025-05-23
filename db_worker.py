import mysql.connector
from config import db_name, db_username, db_password, host, auth_plugin

def get_db_connection():
    return mysql.connector.connect(
    host=host,
    database=db_name,
    user=db_username,
    password=db_password,
    auth_plugin=auth_plugin)