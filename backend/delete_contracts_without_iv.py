"""Delete contracts with 0% IV coverage"""
import os, psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "services", ".env"))

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432"),
    database=os.getenv("DB_NAME", "tradinghub"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD")
)

cursor = conn.cursor()

# Delete contracts with 0 IV
cursor.execute("""
    DELETE FROM options_data
    WHERE (symbol, strike, "right", expiration, bar_interval) IN (
        SELECT symbol, strike, "right", expiration, bar_interval
        FROM options_data
        GROUP BY symbol, strike, "right", expiration, bar_interval
        HAVING COUNT(implied_volatility) = 0
    )
""")

deleted = cursor.rowcount
conn.commit()

print(f"✓ Deleted {deleted} bars from contracts with 0% IV coverage")

cursor.close()
conn.close()
