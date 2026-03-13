
import psycopg2

def reset_table():
    try:
        connection = psycopg2.connect(
            host="localhost",
            database="mydb",
            user="myuser",
            password="mypassword",
            port=5432
        )
        connection.autocommit = True
        cursor = connection.cursor()
        
        print("Truncating table works4cdp_taskgroupassignment...")
        cursor.execute("TRUNCATE TABLE works4cdp_taskp RESTART IDENTITY CASCADE;")
        print("Table truncated and index reset successfully.")
        
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset_table()
