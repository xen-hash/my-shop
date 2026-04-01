"""
routes/admin.py – GadgetHub PH
================================
Admin blueprint: dashboard, product management, order management.
Protected – only accessible by users with is_admin=True.
"""

from flask import (
    Blueprint, render_template, redirect,
    url_for, flash, request
)
from flask_login import login_required, current_user
from functools import wraps
from models import db, Product, Order, User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ── Admin-only decorator ──────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Admin access required.", "danger")
            return redirect(url_for("shop.index"))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    total_products = Product.query.count()
    total_orders   = Order.query.count()
    total_users    = User.query.filter_by(is_admin=False).count()
    total_revenue  = db.session.query(
        db.func.sum(Order.total_price)
    ).filter(Order.status != "pending").scalar() or 0

    recent_orders  = Order.query.order_by(
        Order.created_at.desc()
    ).limit(10).all()

    low_stock = Product.query.filter(
        Product.stock <= 5
    ).order_by(Product.stock.asc()).all()

    return render_template(
        "admin.html",
        view           = "dashboard",
        total_products = total_products,
        total_orders   = total_orders,
        total_users    = total_users,
        total_revenue  = float(total_revenue),
        recent_orders  = recent_orders,
        low_stock      = low_stock,
        title          = "Admin Dashboard – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# PRODUCTS LIST
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/products")
@login_required
@admin_required
def products():
    all_products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template(
        "admin.html",
        view     = "products",
        products = all_products,
        title    = "Manage Products – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# ADD PRODUCT
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/products/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_product():
    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price       = request.form.get("price", 0)
        stock       = request.form.get("stock", 0)
        category    = request.form.get("category", "")
        image_url   = request.form.get("image_url", "").strip()

        if not all([name, description, price, category, image_url]):
            flash("All fields are required.", "danger")
            return redirect(url_for("admin.add_product"))

        if category not in Product.CATEGORIES:
            flash("Invalid category.", "danger")
            return redirect(url_for("admin.add_product"))

        product = Product(
            name        = name,
            description = description,
            price       = float(price),
            stock       = int(stock),
            category    = category,
            image_url   = image_url
        )
        db.session.add(product)
        db.session.commit()

        flash(f'Product "{name}" added successfully!', "success")
        return redirect(url_for("admin.products"))

    return render_template(
        "admin.html",
        view       = "add_product",
        categories = Product.CATEGORIES,
        title      = "Add Product – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# EDIT PRODUCT
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/products/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        product.name        = request.form.get("name", "").strip()
        product.description = request.form.get("description", "").strip()
        product.price       = float(request.form.get("price", 0))
        product.stock       = int(request.form.get("stock", 0))
        product.category    = request.form.get("category", "")
        product.image_url   = request.form.get("image_url", "").strip()

        db.session.commit()
        flash(f'Product "{product.name}" updated!', "success")
        return redirect(url_for("admin.products"))

    return render_template(
        "admin.html",
        view       = "edit_product",
        product    = product,
        categories = Product.CATEGORIES,
        title      = "Edit Product – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# DELETE PRODUCT
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/products/delete/<int:product_id>", methods=["POST"])
@login_required
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    name    = product.name
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{name}" deleted.', "success")
    return redirect(url_for("admin.products"))


# ─────────────────────────────────────────────────────────────
# ORDERS LIST
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/orders")
@login_required
@admin_required
def orders():
    status     = request.args.get("status", "")
    query      = Order.query.order_by(Order.created_at.desc())
    if status and status in Order.STATUSES:
        query  = query.filter_by(status=status)
    all_orders = query.all()

    return render_template(
        "admin.html",
        view           = "orders",
        orders         = all_orders,
        current_status = status,
        statuses       = Order.STATUSES,
        title          = "Manage Orders – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# UPDATE ORDER STATUS
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@login_required
@admin_required
def update_order_status(order_id):
    order      = Order.query.get_or_404(order_id)
    new_status = request.form.get("status")

    if new_status not in Order.STATUSES:
        flash("Invalid status.", "danger")
        return redirect(url_for("admin.orders"))

    order.status = new_status
    db.session.commit()
    flash(f"Order #{order_id:04d} status updated to {new_status}.", "success")
    return redirect(url_for("admin.orders"))