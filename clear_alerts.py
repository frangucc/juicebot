"""Clear all test alerts from the database."""
import os
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres.szuvtcbytepaflthqnal:vLy7fE1GOa070HkB@aws-1-us-east-2.pooler.supabase.com:5432/postgres')

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text('DELETE FROM screener_alerts'))
    conn.commit()
    print(f'✅ Deleted {result.rowcount} test alerts from database')
