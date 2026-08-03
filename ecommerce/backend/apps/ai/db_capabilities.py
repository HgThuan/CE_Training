from django.db import DatabaseError, connections

PRODUCT_EMBEDDING_TABLE = "ai_productembedding"


def product_embedding_table_available(using: str = "default") -> bool:
    """Return whether the optional embedding schema is ready for use."""
    connection = connections[using]
    try:
        return PRODUCT_EMBEDDING_TABLE in connection.introspection.table_names()
    except DatabaseError:
        return False
