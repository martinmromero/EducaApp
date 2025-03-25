import sqlite3

def create_table():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    
    create_table_sql = """
    CREATE TABLE material_materias (
        Id INTEGER PRIMARY KEY AUTOINCREMENT,
        Nombre TEXT NOT NULL
    );
    """
    
    cursor.execute(create_table_sql)
    connection.commit()
    connection.close()

if __name__ == "__main__":
    create_table()
