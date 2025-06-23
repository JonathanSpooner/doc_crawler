import pytest
from unittest.mock import AsyncMock
from pymongo import ASCENDING, DESCENDING
from motor.motor_asyncio import AsyncIOMotorCollection
from doc_crawler.database.indexes.crawl_sessions_indexes import create_crawl_sessions_indexes


async def test_create_crawl_sessions_indexes_success():
    """
    Test successful creation of indexes for the `crawl_sessions` collection.
    """
    # Mock the AsyncIOMotorCollection
    mock_collection = AsyncMock(spec=AsyncIOMotorCollection)
    mock_collection.create_index = AsyncMock()

    # Call the function
    result = await create_crawl_sessions_indexes(mock_collection)

    # Assert the expected indexes were created
    expected_indexes = [
        {
            "keys": [("site_id", ASCENDING), ("status", ASCENDING)],
            "name": "site_status",
            "background": True
        },
        {
            "keys": [("start_time", DESCENDING)],
            "name": "start_time_desc",
            "background": True
        },
        {
            "keys": [
                ("site_id", ASCENDING),
                ("status", ASCENDING),
                ("start_time", DESCENDING)
            ],
            "name": "dashboard_metrics",
            "background": True
        }
    ]

    # Verify each index was created with the correct parameters
    assert mock_collection.create_index.call_count == 3
    for i, expected in enumerate(expected_indexes):
        args, kwargs = mock_collection.create_index.call_args_list[i]
        assert args[0] == expected["keys"]
        assert kwargs["name"] == expected["name"]
        assert kwargs["background"] == expected["background"]

    # Verify the returned list of index names
    assert result == ["site_status", "start_time_desc", "dashboard_metrics"]


async def test_create_crawl_sessions_indexes_failure():
    """
    Test failure case where index creation raises an exception.
    """
    mock_collection = AsyncMock(spec=AsyncIOMotorCollection)
    mock_collection.create_index = AsyncMock(side_effect=Exception("Index creation failed"))

    with pytest.raises(Exception, match="Index creation failed"):
        await create_crawl_sessions_indexes(mock_collection)

    # Verify the function stops after the first failure
    assert mock_collection.create_index.call_count == 1