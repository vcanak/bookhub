"""ORM models.

Importing the models here ensures they are registered on ``Base.metadata`` for
Alembic autogenerate and metadata-based table creation.
"""

from app.models.post import Post
from app.models.user import User

__all__ = ["Post", "User"]
