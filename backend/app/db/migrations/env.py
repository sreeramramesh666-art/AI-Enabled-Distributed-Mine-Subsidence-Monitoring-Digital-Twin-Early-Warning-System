import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add repository root and backend directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "../../.."))
repo_root = os.path.abspath(os.path.join(backend_dir, ".."))

if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from backend.app.core.config import settings
    from backend.app.db.database import Base
    import backend.app.db.models
except ImportError:
    from app.core.config import settings
    from app.db.database import Base
    import app.db.models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_canonical_url() -> str:
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///./") or db_url.startswith("sqlite:///data/"):
        rel_path = db_url.replace("sqlite:///./", "").replace("sqlite:///", "")
        abs_db_path = os.path.join(repo_root, rel_path)
        return f"sqlite:///{abs_db_path}"
    return db_url

def run_migrations_offline() -> None:
    url = get_canonical_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        configuration = {}
    configuration["sqlalchemy.url"] = get_canonical_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

