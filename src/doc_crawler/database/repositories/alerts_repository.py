"""
AlertsRepository implementation for error tracking and notification management.

This repository handles severity-based alert classification, suppression, escalation,
and integration with notification systems.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional
from bson import ObjectId
from pymongo import IndexModel, ASCENDING, DESCENDING
from pydantic import ValidationError

from doc_crawler.database.repositories.async_mongo_repository import AsyncMongoDBRepository
from doc_crawler.database.repositories.sites_repository import SitesRepository


logger = logging.getLogger(__name__)


class Alert:
    """Alert model for error tracking and notifications."""
    def __init__(self, id: ObjectId = None, alert_type: str = None, 
                 severity: str = "medium", title: str = None, 
                 message: str = None, **kwargs):
        self.id = id
        self.alert_type = alert_type
        self.severity = severity
        self.title = title
        self.message = message
        self.site_id = kwargs.get('site_id')
        self.source_component = kwargs.get('source_component')
        self.context = kwargs.get('context', {})
        self.status = kwargs.get('status', 'active')
        self.created_at = kwargs.get('created_at')
        self.resolved_at = kwargs.get('resolved_at')
        self.escalated_at = kwargs.get('escalated_at')
        self.notification_sent = kwargs.get('notification_sent', False)


class AlertSuppression:
    """Alert suppression configuration."""
    def __init__(self, alert_type: str, suppressed_until: datetime, 
                 reason: str = None, **kwargs):
        self.alert_type = alert_type
        self.suppressed_until = suppressed_until
        self.reason = reason
        self.created_at = kwargs.get('created_at')


class AlertStats:
    """Alert statistics for monitoring."""
    def __init__(self, total: int = 0, active: int = 0, resolved: int = 0,
                 by_severity: Dict = None, **kwargs):
        self.total = total
        self.active = active
        self.resolved = resolved
        self.by_severity = by_severity or {}
        self.escalated = kwargs.get('escalated', 0)
        self.suppressed = kwargs.get('suppressed', 0)


class AlertsRepository(AsyncMongoDBRepository):
    """Repository for error tracking and notification management."""
    
    # Alert severity levels (priority order)
    SEVERITY_LEVELS = {
        "critical": 5,
        "high": 4,
        "medium": 3,
        "low": 2,
        "info": 1
    }
    
    def __init__(self, connection_string: str, db_name: str, sites_repository: SitesRepository):
        super().__init__(connection_string, db_name, "alerts")
        self.sites_repository = sites_repository
        self.suppressions_collection = None  # Will be set during initialization

    @classmethod
    async def create(cls, connection_string: str, db_name: str, sites_repository: SitesRepository):
        """Create and initialize a AlertsRepository instance."""
        instance = cls(connection_string, db_name, sites_repository)
        await instance._setup_indexes()
        return instance
    
    async def _setup_indexes(self):
        """Set up collection indexes for optimal performance."""
        # Main alerts indexes
        indexes = [
            IndexModel([("alert_type", ASCENDING), ("site_id", ASCENDING)]),
            IndexModel([("severity", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("site_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("notification_sent", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("escalated_at", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)])
        ]
        await self.create_indexes(indexes)
        
        # Set up suppressions collection
        self.suppressions_collection = self.db["alert_suppressions"]
        await self.suppressions_collection.create_index([
            ("alert_type", ASCENDING),
            ("suppressed_until", ASCENDING)
        ])
    
    def _calculate_alert_hash(self, alert_type: str, site_id: ObjectId = None, 
                            context: Dict = None) -> str:
        """Generate hash for alert deduplication."""
        import hashlib
        
        hash_data = f"{alert_type}:{site_id}:{context}"
        return hashlib.md5(hash_data.encode()).hexdigest()
    
    async def create_alert(self, alert: Alert) -> ObjectId:
        """
        Create a new alert with deduplication.
        
        Args:
            alert: Alert to create
            
        Returns:
            ObjectId of created alert
            
        Raises:
            ValidationError: If alert data is invalid
        """
        try:
            # Validate required fields
            if not alert.alert_type:
                raise ValidationError("Alert type is required")
            if not alert.title:
                raise ValidationError("Alert title is required")
            if alert.severity not in self.SEVERITY_LEVELS:
                raise ValidationError(f"Invalid severity level: {alert.severity}")
            
            # Check if alert type is suppressed
            if await self._is_alert_suppressed(alert.alert_type):
                logger.debug(f"Alert type {alert.alert_type} is suppressed, skipping creation")
                return None
            
            # Generate deduplication hash
            alert_hash = self._calculate_alert_hash(alert.alert_type, alert.site_id, alert.context)
            
            # Check for duplicate active alerts
            existing_alert = await self.find_one({
                "alert_hash": alert_hash,
                "status": "active"
            })
            
            if existing_alert:
                # Update existing alert instead of creating duplicate
                await self.update_one(
                    {"_id": existing_alert["_id"]},
                    {
                        "$set": {"last_seen": datetime.now(UTC)},
                        "$inc": {"occurrence_count": 1}
                    }
                )
                logger.debug(f"Updated existing alert {existing_alert['_id']} instead of creating duplicate")
                return existing_alert["_id"]
            
            # Validate site if provided
            if alert.site_id:
                site_config = await self.sites_repository.get_crawl_configuration(alert.site_id)
                if not site_config:
                    logger.warning(f"Alert references non-existent site {alert.site_id}")
            
            # Create alert document
            now = datetime.now(UTC)
            alert_data = {
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "site_id": alert.site_id,
                "source_component": alert.source_component,
                "context": alert.context,
                "status": "active",
                "alert_hash": alert_hash,
                "occurrence_count": 1,
                "notification_sent": False,
                "created_at": now,
                "last_seen": now
            }
            
            result = await self.insert_one(alert_data, validate=True)
            logger.info(f"Created {alert.severity} alert: {alert.title} (ID: {result})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            raise
    
    async def get_active_alerts(self, severity: str = None) -> List[Alert]:
        """
        Get active alerts, optionally filtered by severity.
        
        Args:
            severity: Optional severity filter
            
        Returns:
            List of active alerts
        """
        try:
            query = {"status": "active"}
            if severity:
                if severity not in self.SEVERITY_LEVELS:
                    raise ValidationError(f"Invalid severity: {severity}")
                query["severity"] = severity
            
            # Sort by severity (critical first) then creation time
            cursor = await self.find_many(
                query,
                sort=[
                    ("severity", DESCENDING),  # Will need custom sort for severity order
                    ("created_at", DESCENDING)
                ]
            )
            
            alerts = []
            for doc in cursor:
                alerts.append(self._document_to_alert(doc))
            
            # Sort by actual severity priority
            alerts.sort(key=lambda a: self.SEVERITY_LEVELS.get(a.severity, 0), reverse=True)
            
            logger.debug(f"Retrieved {len(alerts)} active alerts")
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []
    
    async def resolve_alert(self, alert_id: ObjectId, resolution: str) -> bool:
        """
        Resolve an active alert.
        
        Args:
            alert_id: Alert identifier
            resolution: Resolution description
            
        Returns:
            True if successfully resolved
        """
        try:
            validated_alert_id = self._validate_object_id(alert_id)
            
            update_data = {
                "status": "resolved",
                "resolution": resolution,
                "resolved_at": datetime.now(UTC)
            }
            
            result = await self.update_one(
                {"_id": validated_alert_id, "status": "active"},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Resolved alert {alert_id}: {resolution}")
            else:
                logger.warning(f"Failed to resolve alert {alert_id} - may not be active")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False
    
    async def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """
        Get alert history within specified time range.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of alerts within time range
        """
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)
            
            cursor = await self.find_many(
                {"created_at": {"$gte": since}},
                sort=[("created_at", DESCENDING)]
            )
            
            alerts = []
            for doc in cursor:
                alerts.append(self._document_to_alert(doc))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get alert history: {e}")
            return []
    
    async def suppress_alert_type(self, alert_type: str, duration_hours: int) -> bool:
        """
        Suppress alerts of a specific type for a duration.
        
        Args:
            alert_type: Type of alert to suppress
            duration_hours: Suppression duration in hours
            
        Returns:
            True if suppression successful
        """
        try:
            suppressed_until = datetime.now(UTC) + timedelta(hours=duration_hours)
            
            suppression_data = {
                "alert_type": alert_type,
                "suppressed_until": suppressed_until,
                "created_at": datetime.now(UTC),
                "reason": f"Suppressed for {duration_hours} hours"
            }
            
            # Upsert suppression record
            await self.suppressions_collection.update_one(
                {"alert_type": alert_type},
                {"$set": suppression_data},
                upsert=True
            )
            
            logger.info(f"Suppressed alert type {alert_type} until {suppressed_until}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to suppress alert type {alert_type}: {e}")
            return False
    
    async def get_suppressed_alerts(self) -> List[AlertSuppression]:
        """
        Get currently suppressed alert types.
        
        Returns:
            List of active suppressions
        """
        try:
            now = datetime.now(UTC)
            
            cursor = self.suppressions_collection.find({
                "suppressed_until": {"$gt": now}
            })
            
            suppressions = []
            async for doc in cursor:
                suppressions.append(AlertSuppression(
                    alert_type=doc["alert_type"],
                    suppressed_until=doc["suppressed_until"],
                    reason=doc.get("reason"),
                    created_at=doc.get("created_at")
                ))
            
            return suppressions
            
        except Exception as e:
            logger.error(f"Failed to get suppressed alerts: {e}")
            return []
    
    async def cleanup_old_alerts(self, days_old: int = 30) -> int:
        """
        Clean up old resolved alerts.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of alerts cleaned up
        """
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days_old)
            
            result = await self.delete_many({
                "status": "resolved",
                "resolved_at": {"$lt": cutoff_date}
            })
            
            deleted_count = result.deleted_count
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old alerts")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old alerts: {e}")
            return 0
    
    async def get_alert_statistics(self, days: int = 7) -> AlertStats:
        """
        Get alert statistics for specified period.
        
        Args:
            days: Period in days to analyze
            
        Returns:
            AlertStats object with metrics
        """
        try:
            since = datetime.now(UTC) - timedelta(days=days)
            
            # Aggregate statistics
            pipeline = [
                {"$match": {"created_at": {"$gte": since}}},
                {
                    "$group": {
                        "_id": {
                            "status": "$status",
                            "severity": "$severity"
                        },
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            cursor = await self.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            stats = AlertStats()
            by_severity = {}
            
            for result in results:
                count = result["count"]
                status = result["_id"]["status"]
                severity = result["_id"]["severity"]
                
                stats.total += count
                
                if status == "active":
                    stats.active += count
                elif status == "resolved":
                    stats.resolved += count
                
                if severity not in by_severity:
                    by_severity[severity] = 0
                by_severity[severity] += count
            
            stats.by_severity = by_severity
            
            # Count escalated alerts
            escalated_count = await self.collection.count_documents({
                "created_at": {"$gte": since},
                "escalated_at": {"$exists": True}
            })
            stats.escalated = escalated_count
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get alert statistics: {e}")
            return AlertStats()
    
    async def escalate_unresolved_alerts(self, hours_old: int = 2) -> List[Alert]:
        """
        Escalate unresolved critical and high severity alerts.
        
        Args:
            hours_old: Age threshold for escalation
            
        Returns:
            List of escalated alerts
        """
        try:
            cutoff_time = datetime.now(UTC) - timedelta(hours=hours_old)
            
            # Find unescalated critical/high alerts older than threshold
            query = {
                "status": "active",
                "severity": {"$in": ["critical", "high"]},
                "created_at": {"$lt": cutoff_time},
                "escalated_at": {"$exists": False}
            }
            
            cursor = await self.find_many(query)
            escalated_alerts = []
            
            for doc in cursor:
                # Mark as escalated
                await self.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"escalated_at": datetime.now(UTC)}}
                )
                
                alert = self._document_to_alert(doc)
                escalated_alerts.append(alert)
            
            if escalated_alerts:
                logger.warning(f"Escalated {len(escalated_alerts)} unresolved alerts")
            
            return escalated_alerts
            
        except Exception as e:
            logger.error(f"Failed to escalate alerts: {e}")
            return []
    
    async def _is_alert_suppressed(self, alert_type: str) -> bool:
        """Check if alert type is currently suppressed."""
        try:
            now = datetime.now(UTC)
            doc = await self.suppressions_collection.find_one({
                "alert_type": alert_type,
                "suppressed_until": {"$gt": now}
            })
            return doc is not None
        except Exception:
            return False
    
    def _document_to_alert(self, doc: Dict) -> Alert:
        """Convert MongoDB document to Alert object."""
        return Alert(
            id=doc["_id"],
            alert_type=doc.get("alert_type"),
            severity=doc.get("severity", "medium"),
            title=doc.get("title"),
            message=doc.get("message"),
            site_id=doc.get("site_id"),
            source_component=doc.get("source_component"),
            context=doc.get("context", {}),
            status=doc.get("status", "active"),
            created_at=doc.get("created_at"),
            resolved_at=doc.get("resolved_at"),
            escalated_at=doc.get("escalated_at"),
            notification_sent=doc.get("notification_sent", False)
        )
