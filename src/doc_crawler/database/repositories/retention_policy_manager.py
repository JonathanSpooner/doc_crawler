"""
Data Retention Policies for Philosophy Crawler Database

This module implements automated data retention policies including:
1. TTL (Time-To-Live) indexes for automatic document expiration
2. Archival logic for moving old data to cold storage
3. Monitoring and alerting for retention operations
4. Configuration management for retention settings
"""

import asyncio
import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import json
import gzip

import pymongo
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
import boto3
from botocore.exceptions import ClientError, BotoCoreError

# Configure logging
logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class RetentionPolicy:
    """Configuration for data retention policies"""
    collection_name: str
    ttl_field: str
    retention_days: int
    archive_enabled: bool = False
    archive_after_days: Optional[int] = None
    compression_enabled: bool = True
    
class RetentionPolicyManager:
    """
    Manages data retention policies for MongoDB collections.
    
    Handles:
    - TTL index creation and management
    - Data archival to S3
    - Monitoring and alerting
    - Configuration validation
    """
    
    def __init__(
        self, 
        db: AsyncIOMotorDatabase,
        s3_client: Optional[boto3.client] = None,
        s3_bucket: Optional[str] = None,
        dry_run: bool = False
    ):
        """
        Initialize retention policy manager.
        
        Args:
            db: AsyncIOMotorDatabase instance
            s3_client: Boto3 S3 client for archival operations
            s3_bucket: S3 bucket name for archives
            dry_run: If True, only log operations without executing
        """
        self.db = db
        self.s3_client = s3_client
        self.s3_bucket = s3_bucket
        self.dry_run = dry_run
        
        # Default retention policies
        self.retention_policies = {
            'content_changes': RetentionPolicy(
                collection_name='content_changes',
                ttl_field='detected_at',
                retention_days=365,  # 1 year
                archive_enabled=False
            ),
            'crawl_sessions': RetentionPolicy(
                collection_name='crawl_sessions',
                ttl_field='start_time',
                retention_days=90,   # 3 months in hot storage
                archive_enabled=True,
                archive_after_days=90,
                compression_enabled=True
            ),
            'alerts': RetentionPolicy(
                collection_name='alerts',
                ttl_field='created_at',
                retention_days=180,  # 6 months
                archive_enabled=False
            ),
            'processing_queue': RetentionPolicy(
                collection_name='processing_queue',
                ttl_field='created_at',
                retention_days=30,   # 1 month for completed tasks
                archive_enabled=False
            )
        }
    
    async def setup_ttl_indexes(self) -> Dict[str, bool]:
        """
        Create TTL indexes for all configured collections.
        
        Returns:
            Dict mapping collection names to success status
        """
        results = {}
        
        for policy_name, policy in self.retention_policies.items():
            try:
                collection = self.db[policy.collection_name]
                
                # Check if TTL index already exists
                existing_indexes = await collection.list_indexes().to_list(None)
                ttl_index_exists = any(
                    idx.get('expireAfterSeconds') is not None 
                    for idx in existing_indexes
                )
                
                if ttl_index_exists:
                    logger.info(f"TTL index already exists for {policy.collection_name}")
                    results[policy.collection_name] = True
                    continue
                
                # Calculate expireAfterSeconds
                expire_seconds = policy.retention_days * 24 * 60 * 60
                
                if not self.dry_run:
                    # Create TTL index
                    await collection.create_index(
                        [(policy.ttl_field, pymongo.ASCENDING)],
                        expireAfterSeconds=expire_seconds,
                        name=f"ttl_{policy.ttl_field}",
                        background=True
                    )
                    
                    logger.info(
                        f"Created TTL index for {policy.collection_name} "
                        f"on field '{policy.ttl_field}' with {policy.retention_days} days retention"
                    )
                else:
                    logger.info(
                        f"[DRY RUN] Would create TTL index for {policy.collection_name} "
                        f"on field '{policy.ttl_field}' with {policy.retention_days} days retention"
                    )
                
                results[policy.collection_name] = True
                
            except Exception as e:
                logger.error(f"Failed to create TTL index for {policy.collection_name}: {e}")
                results[policy.collection_name] = False
        
        return results
    
    async def archive_old_documents(self, collection_name: str) -> Dict[str, Any]:
        """
        Archive old documents to S3 before they expire.
        
        Args:
            collection_name: Name of the collection to archive
            
        Returns:
            Dict with archival statistics
        """
        if collection_name not in self.retention_policies:
            raise ValueError(f"No retention policy defined for {collection_name}")
        
        policy = self.retention_policies[collection_name]
        
        if not policy.archive_enabled:
            logger.info(f"Archival not enabled for {collection_name}")
            return {"archived": 0, "status": "disabled"}
        
        if not self.s3_client or not self.s3_bucket:
            logger.error("S3 client or bucket not configured for archival")
            return {"archived": 0, "status": "error", "message": "S3 not configured"}
        
        collection = self.db[collection_name]
        
        # Calculate cutoff date for archival
        cutoff_date = datetime.now(UTC) - timedelta(days=policy.archive_after_days)
        
        # Find documents to archive
        query = {policy.ttl_field: {"$lt": cutoff_date}}
        
        archived_count = 0
        batch_size = 1000
        
        try:
            # Process documents in batches
            async for batch in self._get_batches(collection, query, batch_size):
                if not batch:
                    break
                
                # Archive batch to S3
                archive_key = self._generate_archive_key(collection_name, batch[0], batch[-1])
                success = await self._archive_batch_to_s3(
                    batch, archive_key, policy.compression_enabled
                )
                
                if success:
                    # Remove archived documents from MongoDB
                    if not self.dry_run:
                        doc_ids = [doc['_id'] for doc in batch]
                        result = await collection.delete_many({"_id": {"$in": doc_ids}})
                        archived_count += result.deleted_count
                        
                        logger.info(f"Archived and removed {len(batch)} documents from {collection_name}")
                    else:
                        archived_count += len(batch)
                        logger.info(f"[DRY RUN] Would archive {len(batch)} documents from {collection_name}")
                else:
                    logger.error(f"Failed to archive batch for {collection_name}")
                    break
            
            return {
                "archived": archived_count,
                "status": "success",
                "cutoff_date": cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error during archival of {collection_name}: {e}")
            return {
                "archived": archived_count,
                "status": "error",
                "message": str(e)
            }
    
    async def _get_batches(self, collection, query: Dict, batch_size: int):
        """
        Generator to yield batches of documents for processing.
        """
        skip = 0
        while True:
            batch = await collection.find(query).skip(skip).limit(batch_size).to_list(None)
            if not batch:
                break
            yield batch
            skip += batch_size
    
    def _generate_archive_key(self, collection_name: str, first_doc: Dict, last_doc: Dict) -> str:
        """
        Generate S3 key for archive file.
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        first_id = str(first_doc['_id'])
        last_id = str(last_doc['_id'])
        
        return f"archives/{collection_name}/{timestamp}_{first_id}_{last_id}.json.gz"
    
    async def _archive_batch_to_s3(
        self, 
        documents: List[Dict], 
        s3_key: str, 
        compress: bool = True
    ) -> bool:
        """
        Archive a batch of documents to S3.
        
        Args:
            documents: List of documents to archive
            s3_key: S3 object key
            compress: Whether to compress the archive
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert ObjectIds to strings for JSON serialization
            serializable_docs = []
            for doc in documents:
                serializable_doc = self._make_json_serializable(doc)
                serializable_docs.append(serializable_doc)
            
            # Create JSON content
            json_content = json.dumps(serializable_docs, default=str, indent=2)
            
            if compress:
                # Compress content
                json_bytes = json_content.encode('utf-8')
                compressed_content = gzip.compress(json_bytes)
                content_type = 'application/gzip'
                body = compressed_content
            else:
                content_type = 'application/json'
                body = json_content.encode('utf-8')
            
            if not self.dry_run:
                # Upload to S3
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=s3_key,
                    Body=body,
                    ContentType=content_type,
                    Metadata={
                        'collection': documents[0].get('__collection__', 'unknown') if documents else 'unknown',
                        'document_count': str(len(documents)),
                        'archive_date': datetime.now(UTC).isoformat()
                    }
                )
                
                logger.info(f"Successfully archived {len(documents)} documents to s3://{self.s3_bucket}/{s3_key}")
            else:
                logger.info(f"[DRY RUN] Would archive {len(documents)} documents to s3://{self.s3_bucket}/{s3_key}")
            
            return True
            
        except (ClientError, BotoCoreError) as e:
            logger.error(f"S3 error during archival: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during archival: {e}")
            return False
    
    def _make_json_serializable(self, doc: Dict) -> Dict:
        """
        Convert MongoDB document to JSON-serializable format.
        """
        serializable_doc = {}
        
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                serializable_doc[key] = str(value)
            elif isinstance(value, datetime):
                serializable_doc[key] = value.isoformat()
            elif isinstance(value, dict):
                serializable_doc[key] = self._make_json_serializable(value)
            elif isinstance(value, list):
                serializable_doc[key] = [
                    self._make_json_serializable(item) if isinstance(item, dict) 
                    else str(item) if isinstance(item, ObjectId)
                    else item.isoformat() if isinstance(item, datetime)
                    else item
                    for item in value
                ]
            else:
                serializable_doc[key] = value
        
        return serializable_doc
    
    async def get_retention_status(self) -> Dict[str, Any]:
        """
        Get current retention status for all collections.
        
        Returns:
            Dict with retention statistics for each collection
        """
        status = {}
        
        for policy_name, policy in self.retention_policies.items():
            try:
                collection = self.db[policy.collection_name]
                
                # Get collection stats
                total_docs = await collection.count_documents({})
                
                # Get documents near expiration (within 7 days)
                cutoff_date = datetime.now(UTC) - timedelta(days=policy.retention_days - 7)
                expiring_soon = await collection.count_documents({
                    policy.ttl_field: {"$lt": cutoff_date}
                })
                
                # Check TTL index
                indexes = await collection.list_indexes().to_list(None)
                ttl_index = next(
                    (idx for idx in indexes if idx.get('expireAfterSeconds') is not None),
                    None
                )
                
                status[policy.collection_name] = {
                    "total_documents": total_docs,
                    "expiring_soon": expiring_soon,
                    "retention_days": policy.retention_days,
                    "ttl_index_exists": ttl_index is not None,
                    "ttl_seconds": ttl_index.get('expireAfterSeconds') if ttl_index else None,
                    "archive_enabled": policy.archive_enabled,
                    "archive_after_days": policy.archive_after_days
                }
                
            except Exception as e:
                logger.error(f"Error getting retention status for {policy.collection_name}: {e}")
                status[policy.collection_name] = {"error": str(e)}
        
        return status
    
    async def run_maintenance(self) -> Dict[str, Any]:
        """
        Run all retention maintenance tasks.
        
        Returns:
            Dict with results of all maintenance operations
        """
        logger.info("Starting retention policy maintenance")
        
        results = {
            "ttl_setup": {},
            "archival": {},
            "maintenance_time": datetime.now(UTC).isoformat()
        }
        
        # Setup TTL indexes
        try:
            results["ttl_setup"] = await self.setup_ttl_indexes()
        except Exception as e:
            logger.error(f"Error setting up TTL indexes: {e}")
            results["ttl_setup"] = {"error": str(e)}
        
        # Run archival for enabled collections
        for policy_name, policy in self.retention_policies.items():
            if policy.archive_enabled:
                try:
                    archive_result = await self.archive_old_documents(policy.collection_name)
                    results["archival"][policy.collection_name] = archive_result
                except Exception as e:
                    logger.error(f"Error archiving {policy.collection_name}: {e}")
                    results["archival"][policy.collection_name] = {"error": str(e)}
        
        logger.info("Retention policy maintenance completed")
        return results

# Configuration loader
def load_retention_config(config_path: Optional[str] = None) -> Dict[str, RetentionPolicy]:
    """
    Load retention policies from configuration file.
    
    Args:
        config_path: Path to configuration file (JSON format)
        
    Returns:
        Dict mapping collection names to RetentionPolicy objects
    """
    if not config_path or not Path(config_path).exists():
        logger.info("Using default retention policies")
        return {}
    
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        policies = {}
        for name, policy_data in config_data.items():
            policies[name] = RetentionPolicy(**policy_data)
        
        logger.info(f"Loaded {len(policies)} retention policies from {config_path}")
        return policies
        
    except Exception as e:
        logger.error(f"Error loading retention config from {config_path}: {e}")
        return {}

# CLI script for running maintenance
async def main():
    """
    Main function for running retention maintenance from command line.
    """
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Run database retention maintenance")
    parser.add_argument("--mongodb-uri", default=os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    parser.add_argument("--database", default=os.getenv("DATABASE_NAME", "philosophy_crawler"))
    parser.add_argument("--s3-bucket", default=os.getenv("S3_ARCHIVE_BUCKET"))
    parser.add_argument("--config", help="Path to retention configuration file")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize MongoDB client
    client = AsyncIOMotorClient(args.mongodb_uri)
    db = client[args.database]
    
    # Initialize S3 client if bucket provided
    s3_client = None
    if args.s3_bucket:
        try:
            s3_client = boto3.client('s3')
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
    
    # Create retention manager
    manager = RetentionPolicyManager(
        db=db,
        s3_client=s3_client,
        s3_bucket=args.s3_bucket,
        dry_run=args.dry_run
    )
    
    # Load custom configuration if provided
    if args.config:
        custom_policies = load_retention_config(args.config)
        manager.retention_policies.update(custom_policies)
    
    try:
        # Run maintenance
        results = await manager.run_maintenance()
        
        # Print results
        print(json.dumps(results, indent=2, default=str))
        
        # Get current status
        status = await manager.get_retention_status()
        print("\nCurrent Retention Status:")
        print(json.dumps(status, indent=2, default=str))
        
    except Exception as e:
        logger.error(f"Maintenance failed: {e}")
        return 1
    
    finally:
        client.close()
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))