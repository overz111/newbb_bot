import psycopg2
   from psycopg2 import sql
   import os

   def init_db():
       conn = psycopg2.connect(
           dbname=os.getenv('PG_DBNAME'),
           user=os.getenv('PG_USER'),
           password=os.getenv('PG_PASSWORD'),
           host=os.getenv('PG_HOST'),
           port=os.getenv('PG_PORT')
       )
       c = conn.cursor()
       c.execute('''CREATE TABLE IF NOT EXISTS users (
           id BIGINT PRIMARY KEY, 
           first_name TEXT, 
           last_name TEXT, 
           phone TEXT, 
           username TEXT, 
           role TEXT
       )''')
       c.execute('''CREATE TABLE IF NOT EXISTS events (
           id SERIAL PRIMARY KEY, 
           title TEXT, 
           image_url TEXT
       )''')
       c.execute('''CREATE TABLE IF NOT EXISTS prizes (
           id SERIAL PRIMARY KEY, 
           user_id BIGINT, 
           prize TEXT, 
           date TEXT, 
           status TEXT
       )''')
       c.execute('''CREATE TABLE IF NOT EXISTS promoter_stats (
           id SERIAL PRIMARY KEY, 
           user_id BIGINT, 
           invited_week INTEGER, 
           invited_month INTEGER, 
           qr_code TEXT, 
           activation_date TEXT
       )''')
       conn.commit()
       conn.close()