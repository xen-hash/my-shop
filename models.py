"""
models.py – GadgetHub PH
=========================
SQLAlchemy models for all database tables.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ─────────────────────────────────────────────────────────────
# USER
# ─────────────────────────────────────────────────────────────

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password   = db.Column(db.String(256), nullable=False, default="")
    address    = db.Column(db.Text, nullable=True)
    is_admin   = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    cart_items = db.relationship("CartItem",  backref="user", lazy="dynamic", cascade="all, delete-orphan")
    orders     = db.relationship("Order",     backref="user", lazy="dynamic")
    reviews    = db.relationship("Review",    backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password, password)

    @property
    def cart_count(self) -> int:
        return db.session.query(
            db.func.sum(CartItem.quantity)
        ).filter_by(user_id=self.id).scalar() or 0

    @property
    def cart_total(self) -> float:
        items = CartItem.query.filter_by(user_id=self.id).all()
        return sum(item.subtotal for item in items if item.product.stock > 0)

    def __repr__(self):
        return f"<User {self.email}>"


# ─────────────────────────────────────────────────────────────
# PRODUCT
# ─────────────────────────────────────────────────────────────

class Product(db.Model):
    __tablename__ = "products"

    CATEGORIES = ["earbuds", "chargers", "powerbanks", "accessories"]

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price       = db.Column(db.Float, nullable=False)
    stock       = db.Column(db.Integer, default=0, nullable=False)
    category    = db.Column(db.String(50), nullable=False, index=True)
    image_url   = db.Column(db.Text, nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    cart_items  = db.relationship("CartItem",  backref="product", lazy="dynamic", cascade="all, delete-orphan")
    order_items = db.relationship("OrderItem", backref="product", lazy="dynamic")
    reviews     = db.relationship("Review",    backref="product", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def average_rating(self) -> float:
        reviews = self.reviews.all()
        if not reviews:
            return 0.0
        return round(sum(r.rating for r in reviews) / len(reviews), 1)

    @property
    def review_count(self) -> int:
        return self.reviews.count()

    def __repr__(self):
        return f"<Product {self.name}>"


# ─────────────────────────────────────────────────────────────
# CART ITEM
# ─────────────────────────────────────────────────────────────

class CartItem(db.Model):
    __tablename__ = "cart_items"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"),    nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity   = db.Column(db.Integer, default=1, nullable=False)

    @property
    def subtotal(self) -> float:
        return self.product.price * self.quantity

    def __repr__(self):
        return f"<CartItem user={self.user_id} product={self.product_id} qty={self.quantity}>"


# ─────────────────────────────────────────────────────────────
# ORDER
# ─────────────────────────────────────────────────────────────

class Order(db.Model):
    __tablename__ = "orders"

    STATUSES = [
        "pending",
        "confirmed",
        "order_received",
        "shipped",
        "out_for_delivery",
        "delivered",
        "cancelled",
        "paid",
        "failed_to_deliver",
    ]

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    total_price      = db.Column(db.Float, nullable=False)
    status           = db.Column(db.String(30), default="pending", nullable=False, index=True)
    shipping_address = db.Column(db.Text, nullable=False)
    cancel_reason    = db.Column(db.Text, nullable=True)          # ← used by cancel order & failed_to_deliver
    is_deleted       = db.Column(db.Boolean, default=False, nullable=False)  # soft delete
    created_at       = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    items = db.relationship("OrderItem", backref="order", lazy="joined", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order #{self.id} status={self.status}>"


# ─────────────────────────────────────────────────────────────
# ORDER ITEM
# ─────────────────────────────────────────────────────────────

class OrderItem(db.Model):
    __tablename__ = "order_items"

    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey("orders.id"),   nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity   = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float,   nullable=False)

    @property
    def subtotal(self) -> float:
        return self.unit_price * self.quantity

    def __repr__(self):
        return f"<OrderItem order={self.order_id} product={self.product_id} qty={self.quantity}>"


# ─────────────────────────────────────────────────────────────
# REVIEW
# ─────────────────────────────────────────────────────────────

class Review(db.Model):
    __tablename__ = "reviews"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"),    nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    rating     = db.Column(db.Integer, nullable=False)   # 1–5
    comment    = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Review user={self.user_id} product={self.product_id} rating={self.rating}>"