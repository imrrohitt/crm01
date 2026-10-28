"""
Models package — single source for app-wide model access.
Import all application models here; then use "from app.models import ModelName" everywhere.
Only SQLAlchemy models perform CRUD; schemas are for validation/serialization only.
"""

from app.models.base_model import BaseModel
from app.models.concerns.timestampable import Timestampable
from app.models.concerns.soft_deletable import SoftDeletable
from app.models.concerns.sluggable import Sluggable

# When you add a new model (e.g. app/models/article.py), import and list it here:
# from app.models.article import Article
# __all__ = [..., "Article"]

__all__ = [
    "BaseModel",
    "Timestampable",
    "SoftDeletable",
    "Sluggable",
]
