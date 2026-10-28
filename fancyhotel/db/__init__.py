from dotenv import load_dotenv
from db.mysqldb import MysqlManager

load_dotenv() #loads DB_* variables from the .env file at the repo root

mysqldb = MysqlManager()
#instantiates the database