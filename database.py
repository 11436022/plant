from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

database_url = "mysql+pymysql://plant:1234@localhost/plant_db"

engine = create_engine(database_url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()