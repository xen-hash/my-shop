"""
models.py – GadgetHub PH
========================
All SQLAlchemy ORM models for the application.

Tables
------
  users        – registered shoppers & admins
  products     – tech-accessory catalogue
  cart_items   – per-user shopping cart (cleared on checkout)
  orders       – completed purchase records
  order_items  – line items belonging to an order
  reviews      – product ratings & comments
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt

db    = SQLAlchemy()
bcrypt = Bcrypt()


# ─────────────────────────────────────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────────────────────────────────────

class User(db.Model, UserMixin):
    """
    Represents a registered user (shopper or admin).

    Columns
    -------
    id          PK
    name        full display name
    email       unique login identifier
    password    bcrypt hash
    address     shipping address (free-text)
    is_admin    True  → has access to /admin/* routes
    created_at  UTC timestamp of registration
    """

    __tablename__ = "users"

    id         = db.Column(db.Integer,   primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(150), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)
    address    = db.Column(db.Text,      nullable=True)
    is_admin   = db.Column(db.Boolean,   default=False, nullable=False)
    created_at = db.Column(db.DateTime,  default=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────────────────────
    cart_items = db.relationship("CartItem",  backref="user", lazy=True,
                                 cascade="all, delete-orphan")
    orders     = db.relationship("Order",     backref="user", lazy=True)
    reviews    = db.relationship("Review",    backref="user", lazy=True,
                                 cascade="all, delete-orphan")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def set_password(self, plain_text: str) -> None:
        """Hash and store a plaintext password."""
        self.password = bcrypt.generate_password_hash(plain_text).decode("utf-8")

    def check_password(self, plain_text: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        return bcrypt.check_password_hash(self.password, plain_text)

    @property
    def cart_total(self) -> float:
        """Sum of (price × qty) for every item currently in this user's cart."""
        return sum(item.subtotal for item in self.cart_items)

    @property
    def cart_count(self) -> int:
        """Total number of individual units in the cart."""
        return sum(item.quantity for item in self.cart_items)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} admin={self.is_admin}>"


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTS
# ─────────────────────────────────────────────────────────────────────────────

class Product(db.Model):
    """
    A single product in the GadgetHub catalogue.

    Images are stored as public URLs (no local file uploads).

    Columns
    -------
    id          PK
    name        product title
    description long-form marketing copy
    price       selling price in PHP
    stock       units available; 0 = out of stock
    category    one of: earbuds | chargers | powerbanks | accessories
    image_url   publicly accessible image URL
    created_at  UTC timestamp
    """

    __tablename__ = "products"

    CATEGORIES = ["earbuds", "chargers", "powerbanks", "accessories"]

    id          = db.Column(db.Integer,     primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text,        nullable=False)
    price       = db.Column(db.Numeric(10, 2), nullable=False)
    stock       = db.Column(db.Integer,     default=0, nullable=False)
    category    = db.Column(db.String(50),  nullable=False)
    image_url   = db.Column(db.Text,        nullable=False)
    created_at  = db.Column(db.DateTime,    default=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────────────────────
    cart_items  = db.relationship("CartItem",   backref="product", lazy=True,
                                  cascade="all, delete-orphan")
    order_items = db.relationship("OrderItem",  backref="product", lazy=True)
    reviews     = db.relationship("Review",     backref="product", lazy=True,
                                  cascade="all, delete-orphan")

    # ── Helpers ───────────────────────────────────────────────────────────────
    @property
    def average_rating(self) -> float:
        """Compute mean star rating from all published reviews."""
        if not self.reviews:
            return 0.0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)

    @property
    def review_count(self) -> int:
        return len(self.reviews)

    @property
    def in_stock(self) -> bool:
        return self.stock > 0

    @property
    def stock_label(self) -> str:
        """Human-readable stock status shown on the product card."""
        if self.stock == 0:
            return "Out of Stock"
        if self.stock <= 5:
            return f"Only {self.stock} left!"
        return "In Stock"

    @property
    def price_float(self) -> float:
        """Return price as a Python float (safe for Jinja arithmetic)."""
        return float(self.price)

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name!r} stock={self.stock}>"


# ─────────────────────────────────────────────────────────────────────────────
# CART ITEMS
# ─────────────────────────────────────────────────────────────────────────────

class CartItem(db.Model):
    """
    One row per (user, product) pair in the active cart.

    A user can only have one CartItem per product; the quantity column
    handles multiples.
    """

    __tablename__ = "cart_items"
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),
    )

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"),    nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity   = db.Column(db.Integer, default=1, nullable=False)

    # ── Helpers ───────────────────────────────────────────────────────────────
    @property
    def subtotal(self) -> float:
        """Price of this line item."""
        return float(self.product.price) * self.quantity

    def __repr__(self) -> str:
        return (f"<CartItem user={self.user_id} "
                f"product={self.product_id} qty={self.quantity}>")


# ─────────────────────────────────────────────────────────────────────────────
# ORDERS
# ─────────────────────────────────────────────────────────────────────────────

class Order(db.Model):
    """
    A completed (or pending) purchase by a registered user.

    Status lifecycle:  pending → paid → shipped → delivered
    """

    __tablename__ = "orders"

    STATUSES = ["pending", "paid", "shipped", "delivered"]

    id          = db.Column(db.Integer,      primary_key=True)
    user_id     = db.Column(db.Integer,      db.ForeignKey("users.id"), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    status      = db.Column(db.String(20),   default="pending", nullable=False)
    shipping_address = db.Column(db.Text,    nullable=True)   # snapshot at checkout
    created_at  = db.Column(db.DateTime,     default=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────────────────────
    items = db.relationship("OrderItem", backref="order", lazy=True,
                            cascade="all, delete-orphan")

    # ── Helpers ───────────────────────────────────────────────────────────────
    @property
    def total_float(self) -> float:
        return float(self.total_price)

    @property
    def item_count(self) -> int:
        return sum(i.quantity for i in self.items)

    def __repr__(self) -> str:
        return (f"<Order id={self.id} user={self.user_id} "
                f"total={self.total_price} status={self.status!r}>")


# ─────────────────────────────────────────────────────────────────────────────
# ORDER ITEMS
# ─────────────────────────────────────────────────────────────────────────────

class OrderItem(db.Model):
    """
    One line item within a completed order.

    We snapshot unit_price at checkout so historical orders are
    unaffected by future price changes.
    """

    __tablename__ = "order_items"

    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey("orders.id"),   nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity   = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)  # price at time of order

    # ── Helpers ───────────────────────────────────────────────────────────────
    @property
    def subtotal(self) -> float:
        return float(self.unit_price) * self.quantity

    def __repr__(self) -> str:
        return (f"<OrderItem order={self.order_id} "
                f"product={self.product_id} qty={self.quantity}>")


# ─────────────────────────────────────────────────────────────────────────────
# REVIEWS
# ─────────────────────────────────────────────────────────────────────────────

class Review(db.Model):
    """
    A star rating + optional comment left by a verified buyer.

    Constraint: one review per (user, product) pair.
    """

    __tablename__ = "reviews"
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_review_user_product"),
    )

    id         = db.Column(db.Integer,  primary_key=True)
    user_id    = db.Column(db.Integer,  db.ForeignKey("users.id"),    nullable=False)
    product_id = db.Column(db.Integer,  db.ForeignKey("products.id"), nullable=False)
    rating     = db.Column(db.Integer,  nullable=False)   # 1–5
    comment    = db.Column(db.Text,     nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Validation ────────────────────────────────────────────────────────────
    @staticmethod
    def validate_rating(value: int) -> bool:
        return 1 <= int(value) <= 5

    def __repr__(self) -> str:
        return (f"<Review user={self.user_id} "
                f"product={self.product_id} rating={self.rating}>")