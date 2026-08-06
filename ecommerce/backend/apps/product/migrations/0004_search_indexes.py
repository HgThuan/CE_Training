from django.db import migrations, models


def create_postgres_search_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    statements = (
        "CREATE EXTENSION IF NOT EXISTS pg_trgm",
        """
        CREATE INDEX product_search_vector_gin
        ON product_product
        USING GIN ((
            setweight(
                to_tsvector('simple'::regconfig, COALESCE(name, '')),
                'A'
            )
            ||
            setweight(
                to_tsvector(
                    'simple'::regconfig,
                    COALESCE(short_description, '')
                ),
                'B'
            )
            ||
            setweight(
                to_tsvector('simple'::regconfig, COALESCE(description, '')),
                'C'
            )
        ))
        """,
        """
        CREATE INDEX product_name_trgm_gist
        ON product_product
        USING GIST (name gist_trgm_ops)
        """,
    )
    for statement in statements:
        schema_editor.execute(statement)


def drop_postgres_search_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute("DROP INDEX IF EXISTS product_name_trgm_gist")
    schema_editor.execute("DROP INDEX IF EXISTS product_search_vector_gin")


class Migration(migrations.Migration):
    dependencies = [
        ("product", "0003_normalize_null_variant_barcodes"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["status", "is_deleted", "created_at"],
                name="product_search_feed_idx",
            ),
        ),
        migrations.RunPython(
            create_postgres_search_indexes,
            reverse_code=drop_postgres_search_indexes,
        ),
    ]
