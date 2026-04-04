"""
migrate_add_images_postgres.py – GadgetHub PH
===============================================
PostgreSQL-compatible migration (for Render).
Adds image_url_2 and image_url_3 to products table.

Usage:
    python migrate_add_images_postgres.py
"""

from app import create_app
from models import db
from sqlalchemy import text

def run():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # Check existing columns via information_schema
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'products'
                  AND column_name IN ('image_url_2', 'image_url_3')
            """))
            existing = {row[0] for row in result}

            added = []
            if "image_url_2" not in existing:
                conn.execute(text("ALTER TABLE products ADD COLUMN image_url_2 VARCHAR(500)"))
                added.append("image_url_2")

            if "image_url_3" not in existing:
                conn.execute(text("ALTER TABLE products ADD COLUMN image_url_3 VARCHAR(500)"))
                added.append("image_url_3")

            conn.commit()

        if added:
            print(f"✅ Migration complete. Added columns: {', '.join(added)}")
        else:
            print("✅ No migration needed — columns already exist.")

if __name__ == "__main__":
    run()