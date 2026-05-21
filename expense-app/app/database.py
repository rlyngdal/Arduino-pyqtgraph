import databases
import sqlalchemy
from pathlib import Path

DATABASE_URL = "sqlite+aiosqlite:///./expense_club.db"

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("email", sqlalchemy.String, unique=True, nullable=False),
    sqlalchemy.Column("name", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("picture", sqlalchemy.String),
    sqlalchemy.Column("is_admin", sqlalchemy.Boolean, default=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
)

claims = sqlalchemy.Table(
    "claims",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("user_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("title", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("description", sqlalchemy.Text),
    sqlalchemy.Column("amount", sqlalchemy.Numeric(10, 2), nullable=False),
    sqlalchemy.Column("participants", sqlalchemy.Text),  # JSON string
    sqlalchemy.Column("is_race", sqlalchemy.Boolean, default=False),
    sqlalchemy.Column("status", sqlalchemy.String, default="pending"),  # pending, approved, rejected, paid
    sqlalchemy.Column("admin_comment", sqlalchemy.Text),
    sqlalchemy.Column("submitted_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
    sqlalchemy.Column("reviewed_at", sqlalchemy.DateTime),
    sqlalchemy.Column("paid_at", sqlalchemy.DateTime),
)

claim_files = sqlalchemy.Table(
    "claim_files",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("claim_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("claims.id"), nullable=False),
    sqlalchemy.Column("file_type", sqlalchemy.String, nullable=False),  # receipt, proof
    sqlalchemy.Column("filename", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("original_name", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("uploaded_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
)

engine = sqlalchemy.create_engine(DATABASE_URL.replace("+aiosqlite", ""))


async def init_db():
    metadata.create_all(engine)
    await database.connect()


async def close_db():
    await database.disconnect()
