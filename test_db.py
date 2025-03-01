import psycopg2

password = 'your_actual_password'
print(f"Password length: {len(password)}")

# Try with the new test user
try:
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="algo33"
    )
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {str(e)}") 