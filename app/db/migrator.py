import os
import logging
import asyncpg
from pathlib import Path
from app.config import get_settings

logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """
    Automates the execution of SQL migration files on application startup.
    Reads from the /sql directory and executes files in alphanumeric order.
    """

    def __init__(self):
        self.settings = get_settings()
        # Find the project root (/sql is at the root)
        self.sql_dir = Path(__file__).parent.parent.parent / "sql"

    async def run_migrations(self):
        """
        Connects to Postgres and executes all .sql files in the sql/ directory.
        """
        if not self.settings.database_url:
            logger.info("[MIGRATOR] No database_url in settings. Skipping automated migrations.")
            return

        if not self.sql_dir.exists():
            logger.warning(f"SQL directory not found: {self.sql_dir}. Skipping migrations.")
            return

        # 1. Gather and sort SQL files
        sql_files = sorted([f for f in os.listdir(self.sql_dir) if f.endswith(".sql")])
        if not sql_files:
            logger.info("No SQL migration files found.")
            return

        logger.info(f"Starting automated migrations (found {len(sql_files)} files)...")

        # 2. Connect and execute
        conn = None
        try:
            conn = await asyncpg.connect(self.settings.database_url)
            
            async with conn.transaction():
                for filename in sql_files:
                    file_path = self.sql_dir / filename
                    logger.info(f"Applying migration: {filename}")
                    
                    with open(file_path, "r", encoding="utf-8") as f:
                        sql_content = f.read()
                        
                    # Execute the full SQL content of the file
                    # We rely on IF NOT EXISTS inside the files for idempotency
                    await conn.execute(sql_content)
                    
            logger.info("All migrations applied successfully.")
            
        except Exception as e:
            logger.error(f"Migration failed at {filename if 'filename' in locals() else 'startup'}: {e}")
            # We don't raise here to allow the app to attempt starting anyway, 
            # as Supabase might already be set up manually.
        finally:
            if conn:
                await conn.close()

# Singleton instance
migrator = DatabaseMigrator()
