#!/usr/bin/env python3
"""Run the price_bars table migration."""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

with open('migrations/add_price_bars_table.sql', 'r') as f:
    sql = f.read()

print('Running price_bars migration...')
cursor.execute(sql)
conn.commit()
print('✅ price_bars table created successfully!')

cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'price_bars' ORDER BY ordinal_position")
print('\nColumns created:')
for row in cursor.fetchall():
    print(f'  - {row[0]}')

cursor.close()
conn.close()
