"""
models.py – GadgetHub PH
=========================
UPDATED:
- Product: added specs (JSONB), image_url_2/3
- Product: CATEGORIES expanded to include phones, tablets, laptops
- Order:   is_deleted soft-delete
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    is_admin      = db.Column(db.Boolean, default=False, nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    google_id   = db.Column(db.String(120), unique=True, nullable=True)
    facebook_id = db.Column(db.String(120), unique=True, nullable=True)
    picture     = db.Column(db.String(500), nullable=True)

    orders  = db.relationship("Order",    backref="user", lazy="dynamic")
    cart    = db.relationship("CartItem", backref="user", lazy="dynamic")
    reviews = db.relationship("Review",   backref="user", lazy="dynamic")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def cart_count(self) -> int:
        try:
            return sum(i.quantity for i in self.cart)
        except Exception:
            return 0

    def __repr__(self):
        return f"<User {self.email}>"


class Product(db.Model):
    __tablename__ = "products"

    # ── NEW: expanded categories ──────────────────────────────
    CATEGORIES = [
        "earbuds", "chargers", "powerbanks", "accessories",
        "phones", "tablets", "laptops"
    ]

    # Spec field definitions per category (used by admin form + product page)
    SPEC_FIELDS = {
        "phones": [
            {"name": "display",  "label": "Display",   "placeholder": "6.7\" AMOLED 120Hz"},
            {"name": "ram",      "label": "RAM",        "placeholder": "8GB"},
            {"name": "storage",  "label": "Storage",    "placeholder": "256GB"},
            {"name": "battery",  "label": "Battery",    "placeholder": "5000mAh"},
            {"name": "os",       "label": "OS",         "placeholder": "Android 14"},
            {"name": "camera",   "label": "Camera",     "placeholder": "108MP Triple"},
        ],
        "tablets": [
            {"name": "display",  "label": "Display",   "placeholder": "11\" LCD 90Hz"},
            {"name": "ram",      "label": "RAM",        "placeholder": "6GB"},
            {"name": "storage",  "label": "Storage",    "placeholder": "128GB"},
            {"name": "battery",  "label": "Battery",    "placeholder": "7000mAh"},
            {"name": "os",       "label": "OS",         "placeholder": "Android 13"},
            {"name": "camera",   "label": "Camera",     "placeholder": "13MP"},
        ],
        "laptops": [
            {"name": "display",    "label": "Display",    "placeholder": "15.6\" FHD IPS"},
            {"name": "processor",  "label": "Processor",  "placeholder": "Intel i5-13th Gen"},
            {"name": "ram",        "label": "RAM",        "placeholder": "16GB DDR5"},
            {"name": "storage",    "label": "Storage",    "placeholder": "512GB SSD"},
            {"name": "os",         "label": "OS",         "placeholder": "Windows 11"},
            {"name": "battery",    "label": "Battery",    "placeholder": "72Wh / ~8hrs"},
        ],
        "earbuds": [
            {"name": "driver",     "label": "Driver",     "placeholder": "10mm Dynamic"},
            {"name": "battery",    "label": "Battery",    "placeholder": "30hr total"},
            {"name": "bluetooth",  "label": "Bluetooth",  "placeholder": "BT 5.3"},
            {"name": "anc",        "label": "ANC",        "placeholder": "Yes / No"},
        ],
        "chargers": [
            {"name": "wattage",    "label": "Wattage",    "placeholder": "65W"},
            {"name": "ports",      "label": "Ports",      "placeholder": "2x USB-C, 1x USB-A"},
            {"name": "standard",   "label": "Standard",   "placeholder": "PD 3.0 / QC 4+"},
        ],
        "powerbanks": [
            {"name": "capacity",   "label": "Capacity",   "placeholder": "20000mAh"},
            {"name": "wattage",    "label": "Wattage",    "placeholder": "22.5W"},
            {"name": "ports",      "label": "Ports",      "placeholder": "2x USB-A, 1x USB-C"},
        ],
        "accessories": [],
    }

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price       = db.Column(db.Numeric(10, 2), nullable=False)
    stock       = db.Column(db.Integer, default=0, nullable=False)
    category    = db.Column(db.String(50), nullable=False)
    image_url   = db.Column(db.String(500), nullable=False)
    image_url_2 = db.Column(db.String(500), nullable=True)
    image_url_3 = db.Column(db.String(500), nullable=True)
    specs       = db.Column(db.JSON, nullable=True)   # NEW — structured specs
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    order_items = db.relationship("OrderItem", backref="product", lazy="dynamic")
    cart_items  = db.relationship("CartItem",  backref="product", lazy="dynamic")
    reviews     = db.relationship("Review",    backref="product", lazy="dynamic",
                                  cascade="all, delete-orphan")

    @property
    def price_float(self) -> float:
        return float(self.price) if self.price else 0.0

    @property
    def avg_rating(self) -> float:
        try:
            all_reviews = self.reviews.all()
            if not all_reviews:
                return 0.0
            return round(sum(r.rating for r in all_reviews) / len(all_reviews), 1)
        except Exception:
            return 0.0

    @property
    def average_rating(self) -> float:
        return self.avg_rating

    @property
    def review_count(self) -> int:
        try:
            return self.reviews.count()
        except Exception:
            return 0

    @property
    def extra_images(self) -> list:
        imgs = [self.image_url]
        if self.image_url_2:
            imgs.append(self.image_url_2)
        if self.image_url_3:
            imgs.append(self.image_url_3)
        return imgs

    @property
    def spec_fields(self) -> list:
        """Returns the spec field definitions for this product's category."""
        return self.SPEC_FIELDS.get(self.category, [])

    def __repr__(self):
        return f"<Product {self.name}>"


class Order(db.Model):
    __tablename__ = "orders"

    STATUSES = [
        "pending", "confirmed", "order_received",
        "shipped", "delivered", "paid",
        "cancelled", "failed_to_deliver",
    ]

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    total_price      = db.Column(db.Numeric(12, 2), nullable=False)
    status           = db.Column(db.String(30), default="pending", nullable=False)
    shipping_address = db.Column(db.Text, nullable=True)
    cancel_reason    = db.Column(db.Text, nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_deleted       = db.Column(db.Boolean, default=False, nullable=False)

    items = db.relationship("OrderItem", backref="order", lazy="joined",
                            cascade="all, delete-orphan")

    @property
    def total_float(self) -> float:
        return float(self.total_price) if self.total_price else 0.0

    @property
    def item_count(self) -> int:
        return sum(i.quantity for i in self.items)

    def __repr__(self):
        return f"<Order #{self.id} {self.status}>"


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey("orders.id"),   nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    quantity   = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)

    @property
    def subtotal(self) -> float:
        return float(self.unit_price) * self.quantity


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"),    nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity   = db.Column(db.Integer, default=1, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),
    )

    @property
    def subtotal(self) -> float:
        return float(self.product.price) * self.quantity


class Review(db.Model):
    __tablename__ = "reviews"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"),    nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    rating     = db.Column(db.Integer, nullable=False)
    comment    = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_review_user_product"),
    )