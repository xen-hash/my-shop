"""
seed_db.py – GadgetHub PH
==========================
Run once to:
  1. Create all database tables (CREATE TABLE IF NOT EXISTS).
  2. Insert one admin user.
  3. Insert 12 sample tech-accessory products (images from Unsplash/Pexels URLs).

Usage
-----
    python seed_db.py

Safe to re-run: existing rows are skipped (checked by email / product name).
"""

from app import create_app
from models import db, User, Product

# ─────────────────────────────────────────────────────────────────────────────
# Sample products  (all image_url values point to free CDN images)
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_PRODUCTS = [
    # ── Earbuds ──────────────────────────────────────────────────────────────
    {
        "name": "ProSound AirPods X1",
        "description": (
            "Premium true-wireless earbuds with 30-hour battery life, "
            "active noise cancellation, and IPX5 water resistance. "
            "Crystal-clear call quality with dual microphones."
        ),
        "price": 1299.00,
        "stock": 50,
        "category": "earbuds",
        "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&q=80",
    },
    {
        "name": "BassBoom TWS Pro",
        "description": (
            "Deep-bass true-wireless earbuds with 8mm drivers, "
            "touch controls, and a compact charging case. "
            "Up to 24 hours total playtime."
        ),
        "price": 799.00,
        "stock": 35,
        "category": "earbuds",
        "image_url": "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=600&q=80",
    },
    {
        "name": "SoundWave Neckband BT5",
        "description": (
            "Magnetic neckband earphones with Bluetooth 5.0, "
            "12-hour playback, and fast-charge support. "
            "Perfect for commuters and gym-goers."
        ),
        "price": 549.00,
        "stock": 60,
        "category": "earbuds",
        "image_url": "https://images.unsplash.com/photo-1511367461989-f85a21fda167?w=600&q=80",
    },

    # ── Chargers ─────────────────────────────────────────────────────────────
    {
        "name": "TurboCharge 65W GaN Charger",
        "description": (
            "Compact GaN 65W USB-C charger supports "
            "Power Delivery 3.0 and Quick Charge 4+. "
            "Charges a laptop, phone, and tablet simultaneously."
        ),
        "price": 899.00,
        "stock": 40,
        "category": "chargers",
        "image_url": "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=600&q=80",
    },
    {
        "name": "DualPower 20W Wireless Pad",
        "description": (
            "Dual-coil Qi wireless charging pad. "
            "Charges two devices at once up to 20W. "
            "Slim, non-slip silicone surface."
        ),
        "price": 699.00,
        "stock": 25,
        "category": "chargers",
        "image_url": "https://images.unsplash.com/photo-1616763355548-1b606f439f86?w=600&q=80",
    },
    {
        "name": "MagCharge 15W iPhone Stand",
        "description": (
            "MagSafe-compatible 15W magnetic charging stand. "
            "Adjustable viewing angle, built-in cable management, "
            "and USB-C input for maximum compatibility."
        ),
        "price": 1099.00,
        "stock": 18,
        "category": "chargers",
        "image_url": "https://images.unsplash.com/photo-1603539947678-cd3954ed515d?w=600&q=80",
    },

    # ── Powerbanks ───────────────────────────────────────────────────────────
    {
        "name": "VoltMax 20000mAh Powerbank",
        "description": (
            "High-capacity 20,000mAh powerbank with 22.5W fast charging. "
            "Dual USB-A + 1 USB-C output. "
            "LED battery indicator and pass-through charging."
        ),
        "price": 1499.00,
        "stock": 30,
        "category": "powerbanks",
        "image_url": "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=600&q=80",
    },
    {
        "name": "SlimJuice 10000mAh Thin Pack",
        "description": (
            "Ultra-slim 10,000mAh powerbank at only 9mm thin. "
            "18W USB-C PD output, airline-safe, "
            "and available in 5 colour options."
        ),
        "price": 999.00,
        "stock": 45,
        "category": "powerbanks",
        "image_url": "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=600&q=80",
    },
    {
        "name": "SolarBoost 8000mAh Outdoor Pack",
        "description": (
            "Solar + USB charging hybrid powerbank. "
            "IP67 waterproof, shockproof, and built for outdoor adventures. "
            "Includes built-in LED torch."
        ),
        "price": 1199.00,
        "stock": 4,
        "category": "powerbanks",
        "image_url": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=600&q=80",
    },

    # ── Accessories ───────────────────────────────────────────────────────────
    {
        "name": "ArmourShield Tempered Glass",
        "description": (
            "9H hardness full-cover tempered glass screen protector. "
            "Anti-fingerprint, oleophobic coating, "
            "and precision-cut edges for most flagship phones."
        ),
        "price": 199.00,
        "stock": 200,
        "category": "accessories",
        "image_url": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&q=80",
    },
    {
        "name": "GripStand Universal Phone Mount",
        "description": (
            "360° adjustable universal phone holder for desks and "
            "bedside tables. Compatible with phones 4-inch to 7-inch. "
            "Foldable for travel and storage."
        ),
        "price": 349.00,
        "stock": 75,
        "category": "accessories",
        "image_url": "https://images.unsplash.com/photo-1512054502232-10a0a035d672?w=600&q=80",
    },
    {
        "name": "BraidedCable USB-C 2m",
        "description": (
            "Premium nylon-braided USB-C to USB-C cable (2 metres). "
            "Supports 100W charging and USB 3.1 Gen 2 data transfer. "
            "Tangle-free design with aluminium connectors."
        ),
        "price": 299.00,
        "stock": 0,       # intentionally out of stock for testing
        "category": "accessories",
        "image_url": "https://images.unsplash.com/photo-1615526675159-e248c3021d3f?w=600&q=80",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Seed function
# ─────────────────────────────────────────────────────────────────────────────

def seed():
    app = create_app()

    with app.app_context():
        # 1. Create all tables
        db.create_all()
        print("✅  Tables created (or already exist).")

        # 2. Admin user
        import os
        admin_email    = os.environ.get("ADMIN_EMAIL",    "admin@gadgethub.ph")
        admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@1234")
        admin_name     = "GadgetHub Admin"

        if not User.query.filter_by(email=admin_email).first():
            admin = User(name=admin_name, email=admin_email, is_admin=True)
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print(f"✅  Admin user created  →  {admin_email}")
        else:
            print(f"ℹ️   Admin user already exists  →  {admin_email}")

        # 3. Sample products
        added = 0
        for p in SAMPLE_PRODUCTS:
            if not Product.query.filter_by(name=p["name"]).first():
                db.session.add(Product(**p))
                added += 1

        db.session.commit()
        print(f"✅  {added} product(s) seeded  "
              f"({len(SAMPLE_PRODUCTS) - added} already existed).")

        print("\n🎉  Database ready.  Run:  flask run")


if __name__ == "__main__":
    seed()