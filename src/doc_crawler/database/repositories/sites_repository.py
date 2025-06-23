"""
SitesRepository implementation for managing crawl target configurations.

This repository handles site configuration validation, domain uniqueness enforcement,
health status tracking, and crawl schedule management.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, List, Optional
from bson import ObjectId
from pymongo import IndexModel, ASCENDING

from doc_crawler.database.repositories.async_mongo_repository import AsyncMongoDBRepository
from doc_crawler.database.models.sites import Site, CrawlPatterns, Monitoring
from doc_crawler.config.models import SiteConfiguration
from doc_crawler.database.exceptions import DuplicateResourceError, DatabaseConnectionError


logger = logging.getLogger(__name__)


class SitesRepository(AsyncMongoDBRepository):
    """Repository for managing crawl target configurations and site metadata."""
    
    def __init__(self, connection_string: str, db_name: str):
        super().__init__(connection_string, db_name, "sites")

    @classmethod
    async def create(cls, connection_string: str, db_name: str):
        """Create and initialize a SitesRepository instance."""
        instance = cls(connection_string, db_name)
        await instance._setup_indexes()
        return instance
    
    async def _setup_indexes(self):
        """Set up collection indexes for optimal performance."""
        indexes = [
            IndexModel([("base_url", ASCENDING)], unique=True),
            IndexModel([("monitoring.active", ASCENDING), ("monitoring.next_scheduled_crawl", ASCENDING)]),
            IndexModel([("tags", ASCENDING)]),
            IndexModel([("created_at", ASCENDING)]),
            IndexModel([("monitoring.frequency", ASCENDING), ("monitoring.active", ASCENDING)])
        ]
        await self.collection.create_indexes(indexes)
    
    async def create_site(self, site_config: SiteConfiguration) -> ObjectId:
        """
        Create a new site configuration.
        
        Args:
            site_config: Site configuration data
            
        Returns:
            ObjectId of the created site
            
        Raises:
            ValidationError: If site configuration is invalid
            DuplicateResourceError: If domain already exists
        """
        try:
            # Validate site configuration
            site_config_dict = site_config.model_dump()
            
            # Check for domain uniqueness
            existing_site = await self.find_one({"base_url": site_config.base_url})
            if existing_site:
                raise DuplicateResourceError(f"Site with base_url {site_config.base_url} already exists")
            
            # Create site document
            now = datetime.now(UTC)
            site_data = {
                "name": site_config.name,
                "base_url": str(site_config.base_url),
                "crawl_patterns": {
                    "allowed_domains": site_config.domains,
                    "start_urls": [str(site_config.base_url)],
                    "deny_patterns": [pattern.pattern for pattern in site_config.denied_urls],
                    "allow_patterns": [pattern.pattern for pattern in site_config.allowed_urls]
                },
                "politeness": {
                    "delay": site_config.delay or 1.0,
                    "user_agent": "PhilosophyCrawler/1.0",
                    "retry_policy": {
                        "max_retries": 3,
                        "retry_delay": 2000
                    }
                },
                "monitoring": {
                    "active": site_config.enabled,
                    "frequency": "daily",
                    "last_crawl_time": None,
                    "next_scheduled_crawl": now if site_config.enabled else None
                },
                "tags": getattr(site_config, 'tags', []),
                "health_status": "unknown",
                "created_at": now,
                "updated_at": now
            }
            
            result = await self.insert_one(site_data, validate=True)
            logger.info(f"Created site configuration for {site_config.name} with ID {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create site configuration: {e}")
            if "connection" in str(e).lower():
                raise DatabaseConnectionError(f"Database connection failed: {e}")
            if isinstance(e, DuplicateResourceError):
                raise  # Re-raise the original DuplicateResourceError
            raise ValueError(f"Site creation failed: {e}")
    
    async def get_active_sites(self) -> List[Site]:
        """
        Get all active sites for crawling.
        
        Returns:
            List of active Site objects
        """
        try:
            cursor = await self.find_many(
                {"monitoring.active": True},
                sort=[("monitoring.next_scheduled_crawl", ASCENDING)]
            )
            
            sites = []
            for doc in cursor:
                sites.append(self._document_to_site(doc))
            
            logger.debug(f"Retrieved {len(sites)} active sites")
            return sites
            
        except Exception as e:
            logger.error(f"Failed to get active sites: {e}")
            return []
    
    async def get_site_by_domain(self, domain: str) -> Optional[Site]:
        """
        Get site by domain name.
        
        Args:
            domain: Domain name to search for
            
        Returns:
            Site object if found, None otherwise
        """
        try:
            # Normalize domain for search
            if not domain.startswith(('http://', 'https://')):
                search_patterns = [f"http://{domain}", f"https://{domain}"]
            else:
                search_patterns = [domain]
            
            for pattern in search_patterns:
                doc = await self.find_one({"base_url": {"$regex": f"^{pattern}"}})
                if doc:
                    return self._document_to_site(doc)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get site by domain {domain}: {e}")
            return None
    
    async def update_crawl_settings(self, site_id: ObjectId, settings: Dict) -> bool:
        """
        Update crawl settings for a site.
        
        Args:
            site_id: Site identifier
            settings: Settings to update
            
        Returns:
            True if update successful
        """
        try:
            validated_site_id = self._validate_object_id(site_id)
            
            update_data = {
                "updated_at": datetime.now(UTC)
            }
            
            # Map settings to document structure
            if "delay" in settings:
                update_data["politeness.delay"] = float(settings["delay"])
            if "max_concurrent" in settings:
                update_data["politeness.max_concurrent"] = int(settings["max_concurrent"])
            if "allowed_domains" in settings:
                update_data["crawl_patterns.allowed_domains"] = settings["allowed_domains"]
            
            result = await self.update_one(
                {"_id": validated_site_id},
                {"$set": update_data},
                validate=True
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Updated crawl settings for site {site_id}")
            else:
                logger.warning(f"No crawl settings updated for site {site_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to update crawl settings for site {site_id}: {e}")
            return False
    
    async def disable_site(self, site_id: ObjectId, reason: str) -> bool:
        """
        Disable a site from crawling.
        
        Args:
            site_id: Site identifier
            reason: Reason for disabling
            
        Returns:
            True if successfully disabled
        """
        try:
            validated_site_id = self._validate_object_id(site_id)
            
            update_data = {
                "monitoring.active": False,
                "monitoring.next_scheduled_crawl": None,
                "disabled_reason": reason,
                "disabled_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC)
            }
            
            result = await self.update_one(
                {"_id": validated_site_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Disabled site {site_id}: {reason}")
            else:
                logger.warning(f"Failed to disable site {site_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to disable site {site_id}: {e}")
            return False
    
    async def get_sites_for_crawl_schedule(self, schedule_type: str) -> List[Site]:
        """
        Get sites scheduled for crawling by schedule type.
        
        Args:
            schedule_type: Type of schedule (daily, weekly, monthly)
            
        Returns:
            List of sites matching schedule
        """
        try:
            now = datetime.now(UTC)
            
            query = {
                "monitoring.active": True,
                "monitoring.frequency": schedule_type,
                "$or": [
                    {"monitoring.next_scheduled_crawl": {"$lte": now}},
                    {"monitoring.next_scheduled_crawl": None}
                ]
            }
            
            cursor = await self.find_many(
                query,
                sort=[("monitoring.last_crawl_time", ASCENDING)]
            )
            
            sites = []
            for doc in cursor:
                sites.append(self._document_to_site(doc))
            
            logger.debug(f"Retrieved {len(sites)} sites for {schedule_type} schedule")
            return sites
            
        except Exception as e:
            logger.error(f"Failed to get sites for schedule {schedule_type}: {e}")
            return []
    
    async def update_site_health_status(self, site_id: ObjectId, status: str) -> bool:
        """
        Update site health status.
        
        Args:
            site_id: Site identifier
            status: Health status (healthy, unhealthy, unknown)
            
        Returns:
            True if update successful
        """
        try:
            validated_site_id = self._validate_object_id(site_id)
            
            update_data = {
                "health_status": status,
                "health_checked_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC)
            }
            
            result = await self.update_one(
                {"_id": validated_site_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.debug(f"Updated health status for site {site_id} to {status}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update health status for site {site_id}: {e}")
            return False
    
    async def get_crawl_configuration(self, site_id: ObjectId) -> Optional[Dict]:
        """
        Get complete crawl configuration for a site.
        
        Args:
            site_id: Site identifier
            
        Returns:
            Crawl configuration dictionary
        """
        try:
            validated_site_id = self._validate_object_id(site_id)
            
            doc = await self.find_one({"_id": validated_site_id})
            if not doc:
                return None
            
            # Extract crawl configuration
            config = {
                "site_id": str(doc["_id"]),
                "name": doc["name"],
                "base_url": doc["base_url"],
                "crawl_patterns": doc.get("crawl_patterns", {}),
                "politeness": doc.get("politeness", {}),
                "monitoring": doc.get("monitoring", {}),
                "health_status": doc.get("health_status", "unknown")
            }
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to get crawl configuration for site {site_id}: {e}")
            return None
    
    def _document_to_site(self, doc: Dict) -> Site:
        """Convert MongoDB document to Site object."""
        crawl_patterns = CrawlPatterns(
            allowed_domains=doc.get("crawl_patterns", {}).get("allowed_domains", []),
            start_urls=doc.get("crawl_patterns", {}).get("start_urls", []),
            deny_patterns=doc.get("crawl_patterns", {}).get("deny_patterns", []),
            allow_patterns=doc.get("crawl_patterns", {}).get("allow_patterns", [])
        )
        
        monitoring = Monitoring(
            active=doc.get("monitoring", {}).get("active", False),
            frequency=doc.get("monitoring", {}).get("frequency", "daily"),
            last_crawl_time=doc.get("monitoring", {}).get("last_crawl_time"),
            next_scheduled_crawl=doc.get("monitoring", {}).get("next_scheduled_crawl")
        )
        
        return Site(
            id=doc["_id"],
            name=doc["name"],
            base_url=doc["base_url"],
            crawl_patterns=crawl_patterns,
            monitoring=monitoring,
            tags=doc.get("tags", []),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at")
        )
