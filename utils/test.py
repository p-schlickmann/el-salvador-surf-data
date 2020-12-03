from utils.conn import DatabaseConnection

with DatabaseConnection('./data.db') as cursor:
    cursor.execute('DELETE FROM results WHERE date="31-3-2015"')