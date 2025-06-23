from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Type
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClient, AsyncIOMotorClientSession
from datetime import datetime
import logging
import os # For simulating loading migrations (in real scenario)
import inspect # For dynamic loading of migration classes

logger = logging.getLogger(__name__)

# Base Migration Class
class Migration(ABC):
    """
    Abstract base class for a database migration. Each migration must define
    a unique version, a description, and 'up'/'down' methods.
    """
    version: int
    description: str
    
    @abstractmethod
    async def up(self, database: AsyncIOMotorDatabase, session: Optional[AsyncIOMotorClientSession] = None) -> None:
        """Applies the migration (forwards)."""
        pass
    
    @abstractmethod
    async def down(self, database: AsyncIOMotorDatabase, session: Optional[AsyncIOMotorClientSession] = None) -> None:
        """Rolls back the migration (backwards)."""
        pass

# Example Migration (This would represent a file in the 'versions' folder)
# In a real system, these would be loaded dynamically.
# For demonstration purposes, we might define some dummy migrations here or within _load_migrations.
# Example:
# class Version001InitialSetup(Migration):
#     version = 1
#     description = "Initial collection and index setup"
#     async def up(self, database: AsyncIOMotorDatabase, session: Optional[AsyncIOMotorClientSession] = None) -> None:
#         print("Running initial setup migration UP")
#         # Use CollectionManager here
#         # from database.models.collections import CollectionManager
#         # manager = CollectionManager(database)
#         # await manager.create_collections()
#         # await manager.create_indexes()
#     async def down(self, database: AsyncIOMotorDatabase, session: Optional[AsyncIOMotorClientSession] = None) -> None:
#         print("Running initial setup migration DOWN")
#         # drop collections/indexes

class MigrationManager:
    """
    Manages database schema migrations, including running, rolling back,
    and creating new migration files.
    """
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.migrations_collection = database.schema_migrations
        self.database_client = database.client # Used for starting transactions
    
    async def _ensure_migrations_collection(self) -> None:
        """Ensures the schema_migrations collection exists."""
        collection_names = await self.database.list_collection_names()
        if "schema_migrations" not in collection_names:
            logger.info("Creating 'schema_migrations' collection.")
            await self.database.create_collection("schema_migrations")
            await self.migrations_collection.create_index([("version", 1)], unique=True)
            logger.info("Collection 'schema_migrations' created with unique index.")

    async def get_current_version(self) -> int:
        """Retrieves the current database schema version from the migration history."""
        await self._ensure_migrations_collection()
        try:
            # Sort by version descending and get the first (latest)
            latest_migration = await self.migrations_collection.find_one(
                {}, sort=[("version", -1)]
            )
            version = latest_migration["version"] if latest_migration else 0
            logger.info(f"Current database schema version: {version}")
            return version
        except Exception as e:
            logger.error(f"Error getting current migration version: {e}", exc_info=True)
            raise

    def _load_migrations(self) -> List[Type[Migration]]:
        """
        Dynamically loads migration classes from the 'versions' directory.
        In a real application, this would read files from a specific directory.
        For this simulation, we'll use a placeholder or assume migrations are "registered".
        """
        migrations_list: List[Type[Migration]] = []
        # Simulate loading: In a real scenario, you'd iterate through files in
        # database/migrations/versions/, import them, and find classes inheriting from Migration.
        
        # Example of how a migration file might be structured:
        # from database.migrations.manager import Migration
        # class Version001InitialSetup(Migration): ...
        
        # For demonstration purposes, define a static list or import known ones
        # This part requires a bit of manual setup or a mock for testing purposes.
        # To make this functional without complex file system traversal and dynamic imports,
        # we'll assume migrations are somehow made available.
        # As per the task, I will not write the actual filesystem traversal code, but
        # conceptually this method would populate `migrations_list`.
        
        # Placeholder for actual migrations (e.g., in a 'versions' directory)
        # Assuming for now there's just one example migration for demonstration
        class DummyMigration001(Migration):
            version = 1
            description = "Dummy initial setup"
            async def up(self, database: AsyncIOMotorDatabase, session: Optional[AsyncIOMotorClientSession] = None) -> None:
                logger.info("Running DummyMigration001 UP")
                # This would call CollectionManager to create collections/indexes
                from database.models.collections import CollectionManager
                manager = CollectionManager(database)
                await manager.create_collections()
                await manager.create_indexes()
                logger.info("DummyMigration001 UP finished.")
            async def down(self, database: AsyncIOMotorDatabase, session: Optional[AsyncIOMotorClientSession] = None) -> None:
                logger.info("Running DummyMigration001 DOWN")
                # Example: dropping a collection created in UP
                # await database.test_collection.drop()
                logger.info("DummyMigration001 DOWN finished.")

        class DummyMigration002(Migration):
            version = 2
            description = "Add new 'metadata.author' field to Pages"
            async def up(self, database: AsyncIOMotorDatabase, session: Optional[AsyncIOMotorClientSession] = None) -> None:
                logger.info("Running DummyMigration002 UP: Adding 'metadata.author' to Pages")
                await database.pages.update_many(
                    {},
                    {
                        "$set": {"metadata.author": "Unknown"},
                        "$currentDate": {"updated_at": True}
                    },
                    session=session
                )
                logger.info("DummyMigration002 UP finished.")

            async def down(self, database: AsyncIOMotorDatabase, session: Optional[AsyncIOMotorClientSession] = None) -> None:
                logger.info("Running DummyMigration002 DOWN: Removing 'metadata.author' from Pages")
                await database.pages.update_many(
                    {},
                    {
                        "$unset": {"metadata.author": ""},
                        "$currentDate": {"updated_at": True}
                    },
                    session=session
                )
                logger.info("DummyMigration002 DOWN finished.")


        migrations_list.append(DummyMigration001)
        migrations_list.append(DummyMigration002)

        # Sort migrations by version number to ensure correct order
        migrations_list.sort(key=lambda m: m.version)
        logger.debug(f"Loaded migrations: {[m.version for m in migrations_list]}")
        return migrations_list

    async def run_migrations(self, target_version: Optional[int] = None) -> None:
        """
        Runs pending migrations up to a specific target version, or all pending migrations.
        Ensures migrations are run atomically within transactions.
        """
        await self._ensure_migrations_collection()
        current_version = await self.get_current_version()
        migrations = self._load_migrations()
        
        migrations_to_run = [m for m in migrations if m.version > current_version]
        if target_version is not None:
            migrations_to_run = [m for m in migrations_to_run if m.version <= target_version]
        
        if not migrations_to_run:
            logger.info("No new migrations to run.")
            return

        logger.info(f"Running migrations from version {current_version} up to {target_version if target_version is not None else 'latest'}.")
        for migration in migrations_to_run:
            logger.info(f"Applying migration V{migration.version}: {migration.description}")
            async with await self.database_client.start_session() as session:
                async with session.start_transaction():
                    try:
                        await migration.up(self.database, session)
                        await self.migrations_collection.insert_one(
                            {"version": migration.version, "description": migration.description, "applied_at": datetime.utcnow()},
                            session=session
                        )
                        await session.commit_transaction()
                        logger.info(f"Migration V{migration.version} applied and committed successfully.")
                    except Exception as e:
                        await session.abort_transaction()
                        logger.error(f"Migration V{migration.version} failed and transaction aborted: {e}", exc_info=True)
                        raise # Re-raise to stop the migration process

    async def rollback_migration(self, version: int) -> None:
        """
        Rolls back a specific migration version. This assumes 'down' methods
        are idempotent and correctly reverse the 'up' changes.
        """
        await self._ensure_migrations_collection()
        current_version = await self.get_current_version()
        if version >= current_version:
            logger.warning(f"Cannot rollback future or current version. Requested: {version}, Current: {current_version}")
            return
        
        migrations = self._load_migrations()
        migration_to_rollback = next((m for m in migrations if m.version == version), None)
        
        if not migration_to_rollback:
            logger.warning(f"Migration V{version} not found in loaded migrations. Cannot rollback.")
            return

        logger.info(f"Rolling back migration V{migration_to_rollback.version}: {migration_to_rollback.description}")
        async with await self.database_client.start_session() as session:
            async with session.start_transaction():
                try:
                    await migration_to_rollback.down(self.database, session)
                    await self.migrations_collection.delete_one(
                        {"version": migration_to_rollback.version},
                        session=session
                    )
                    await session.commit_transaction()
                    logger.info(f"Migration V{migration_to_rollback.version} rolled back and committed successfully.")
                except Exception as e:
                    await session.abort_transaction()
                    logger.error(f"Rollback of migration V{migration_to_rollback.version} failed and transaction aborted: {e}", exc_info=True)
                    raise

    async def create_migration(self, name: str) -> str:
        """
        Generates a new migration file template with a new version number.
        The name should be descriptive (e.g., "add_new_status_field").
        """
        await self._ensure_migrations_collection()
        current_version = await self.get_current_version()
        new_version = current_version + 1
        
        file_name = f"V{new_version:03d}_{name.replace(' ', '_').lower()}.py"
        template = f'''
from database.migrations.manager import Migration
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClientSession
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Version{new_version:03d}{name.replace(" ", "").title()}(Migration):
    version = {new_version}
    description = "{name}"

    async def up(self, database: AsyncIOMotorDatabase, session: Optional[AsyncIOMotorClientSession] = None) -> None:
        """
        Apply the migration.
        e.g., create a new collection, add/modify fields, create indexes.
        """
        logger.info(f"Applying migration V{{self.version}}: {{self.description}} (UP)")
        # Example:
        # await database.your_new_collection.insert_one({{"field": "value"}}, session=session)
        # await database.existing_collection.update_many({{"old_field": {{"$exists": True}}}}, {{"$rename": {{"old_field": "new_field"}}}}, session=session)
        # await database.existing_collection.create_index({{"new_field": 1}})
        
        logger.info(f"Migration V{{self.version}} UP complete.")

    async def down(self, database: AsyncIOMotorDatabase, session: Optional[AsyncIOMotorClientSession] = None) -> None:
        """
        Rollback the migration.
        e.g., drop a new collection, revert field changes, drop indexes.
        WARNING: Rollback should be carefully tested.
        """
        logger.info(f"Rolling back migration V{{self.version}}: {{self.description}} (DOWN)")
        # Example:
        # await database.your_new_collection.drop(session=session)
        # await database.existing_collection.update_many({{"new_field": {{"$exists": True}}}}, {{"$rename": {{"new_field": "old_field"}}}}, session=session)
        # await database.existing_collection.drop_index("new_field_1")

        logger.info(f"Migration V{{self.version}} DOWN complete.")
        '''
        logger.info(f"Generated migration template for V{new_version} ('{name}') as '{file_name}'.")
        return template