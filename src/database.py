# import psycopg2
# import logging

# from utils.config import DB_HOST, DB_PORT, DB_DATABASE, DB_USER, DB_PASS


# logger = logging.getLogger(__name__)


# def test_database():
#     try:
#         conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_DATABASE, user=DB_USER, password=DB_PASS)
#         conn.autocommit = True
#     except Exception as error:
#         logger.error(error)
#         return None

#     table = 'mytable'

#     with conn.cursor() as cur:
#         try:
#             cur.execute(f"CREATE TABLE IF NOT EXISTS {table} (my_id SERIAL PRIMARY KEY, my_string VARCHAR(255))")
#             cur.execute(f"INSERT INTO  {table} (my_string) VALUES ('MyTest') ON CONFLICT DO NOTHING")
#             cur.execute(f"SELECT * FROM {table}")
#             result = cur.fetchone()
#             logger.info(str(result))

#         except (Exception, psycopg2.DatabaseError) as error:
#             logger.error(error)
#             return None

#     return 'ok'
