import pytest
from datetime import datetime, UTC
from bson import ObjectId
from doc_crawler.database.models.author_works import AuthorWork, PyObjectId

def test_author_work_creation():
    """Test basic creation of an AuthorWork instance."""
    work = AuthorWork(
        author_name="Immanuel Kant",
        work_title="Critique of Pure Reason",
        publication_date="1781-01-01",
        site_id=str(ObjectId()),
        page_id=str(ObjectId()),
        work_id="ISBN-1234567890",
        tags=["philosophy", "enlightenment"],
    )

    assert work.author_name == "Immanuel Kant"
    assert work.work_title == "Critique of Pure Reason"
    assert work.publication_date == "1781-01-01"
    assert isinstance(work.site_id, str)
    assert isinstance(work.page_id, str)
    assert work.work_id == "ISBN-1234567890"
    assert work.tags == ["philosophy", "enlightenment"]
    assert isinstance(work.created_at, datetime)
    assert isinstance(work.updated_at, datetime)

def test_author_work_defaults():
    """Test defaults for optional fields."""
    work = AuthorWork(
        author_name="Friedrich Nietzsche",
        work_title="Thus Spoke Zarathustra",
        site_id=str(ObjectId()),
        page_id=str(ObjectId()),
    )

    assert work.publication_date is None
    assert work.work_id is None
    assert work.tags == []
    assert work.created_at <= datetime.now(UTC)
    assert work.updated_at <= datetime.now(UTC)

def test_author_work_publication_date_validation_valid():
    """Test valid publication date formats."""
    valid_dates = ["2023-01-01", "1999-12-31", None]
    for date in valid_dates:
        work = AuthorWork(
            author_name="Test Author",
            work_title="Test Work",
            publication_date=date,
            site_id=str(ObjectId()),
            page_id=str(ObjectId()),
        )
        assert work.publication_date == date

def test_author_work_publication_date_validation_invalid():
    """Test invalid publication date formats."""
    invalid_dates = ["2023/01/01", "31-12-1999", "Jan 1, 2023", ""]
    for date in invalid_dates:
        with pytest.raises(ValueError, match="Publication date must be in the format 'YYYY-MM-DD'."):
            AuthorWork(
                author_name="Test Author",
                work_title="Test Work",
                publication_date=date,
                site_id=str(ObjectId()),
                page_id=str(ObjectId()),
            )

def test_author_work_id_alias():
    """Test that `_id` is aliased to `id`."""
    work_id = ObjectId()
    work = AuthorWork(
        _id=work_id,
        author_name="Test Author",
        work_title="Test Work",
        site_id=str(ObjectId()),
        page_id=str(ObjectId()),
    )
    assert work.id == str(work_id)

def test_author_work_objectid_serialization():
    """Test PyObjectId serialization."""
    object_id = ObjectId()
    work = AuthorWork(
        author_name="Test Author",
        work_title="Test Work",
        site_id=object_id,
        page_id=object_id,
    )
    assert isinstance(work.site_id, str)
    assert isinstance(work.page_id, str)
    assert work.site_id == str(object_id)
    assert work.page_id == str(object_id)
