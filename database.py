import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
db_name = os.getenv("DB_NAME")

database_url = f"mysql+pymysql://{user}:{password}@{host}/{db_name}"

engine = create_engine(database_url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()