"""
migrate_add_cancel_reason.py – GadgetHub PH
============================================
One-time migration: adds the `cancel_reason` column to the `orders` table.
Safe to re-run — skips if the column already exists.

Usage:
    python migrate_add_cancel_reason.py
"""

from app import create_app
from models import db

def run():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(db.text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'orders'
                  AND column_name = 'cancel_reason'
            """))
            exists = result.fetchone()

            if exists:
                print("✅  Column 'cancel_reason' already exists — nothing to do.")
            else:
                conn.execute(db.text("""
                    ALTER TABLE orders
                    ADD COLUMN cancel_reason TEXT
                """))
                conn.commit()
                print("✅  Column 'cancel_reason' successfully added to 'orders' table.")

if __name__ == "__main__":
    run()