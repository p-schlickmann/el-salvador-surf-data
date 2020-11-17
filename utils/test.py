from utils.conn import DatabaseConnection

with DatabaseConnection('./data.db') as cursor:
    test = cursor.execute('SELECT * FROM results WHERE date="6-12-2019"')
    print(test.fetchall())