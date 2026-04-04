"""
admin.py – GadgetHub PH
================================
Admin blueprint: dashboard, product management, order management,
revenue analytics, stock management, user management.
Protected – only accessible by users with is_admin=True.

FIXES / ENHANCEMENTS:
1. Customers page: robust error handling + uses pre-built order_counts dict
2. Products: add/edit now support image_url_2 and image_url_3
3. Dashboard: soft-delete (hide) endpoint for paid/delivered orders
4. Email notification on order status update (already wired, kept)
5. Large-screen / mobile improvements are CSS-only (in admin.html)
"""

from flask import (
    Blueprint, render_template, redirect,
    url_for, flash, request, jsonify
)
from flask_login import login_required, current_user
from functools import wraps
from models import db, Product, Order, User, OrderItem, Review
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

TERMINAL_STATUSES  = ["paid", "cancelled", "failed_to_deliver", "delivered"]
DELETABLE_STATUSES = ["paid", "delivered"]


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
    # These counts always reflect ALL historical data (never filtered by is_deleted)
    total_products = Product.query.count()
    total_orders   = Order.query.count()
    total_users    = User.query.filter_by(is_admin=False).count()
    total_revenue  = db.session.query(
        db.func.sum(Order.total_price)
    ).filter(Order.status != "pending").scalar() or 0

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_revenue = db.session.query(
        db.func.sum(Order.total_price)
    ).filter(
        Order.created_at >= seven_days_ago,
        Order.status != "pending"
    ).scalar() or 0

    status_counts = {}
    for s in Order.STATUSES:
        status_counts[s] = Order.query.filter_by(status=s).count()

    daily_revenue = []
    daily_labels  = []
    for i in range(6, -1, -1):
        day       = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = day_start + timedelta(days=1)
        rev = db.session.query(db.func.sum(Order.total_price)).filter(
            Order.created_at >= day_start,
            Order.created_at < day_end,
            Order.status != "pending"
        ).scalar() or 0
        daily_revenue.append(float(rev))
        daily_labels.append(day.strftime("%b %d"))

    # Dashboard "recent orders" table only shows non-deleted orders
    recent_orders  = Order.query.filter_by(is_deleted=False).order_by(
        Order.created_at.desc()
    ).limit(10).all()
    low_stock      = Product.query.filter(Product.stock <= 5).order_by(Product.stock.asc()).all()
    pending_orders = Order.query.filter_by(status="pending", is_deleted=False).count()

    return render_template(
        "admin.html",
        view              = "dashboard",
        total_products    = total_products,
        total_orders      = total_orders,
        total_users       = total_users,
        total_revenue     = float(total_revenue),
        recent_revenue    = float(recent_revenue),
        status_counts     = status_counts,
        daily_revenue     = json.dumps(daily_revenue),
        daily_labels      = json.dumps(daily_labels),
        recent_orders     = recent_orders,
        low_stock         = low_stock,
        pending_orders    = pending_orders,
        deletable_statuses = DELETABLE_STATUSES,
        title             = "Admin Dashboard – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# REAL-TIME POLL ENDPOINT
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/api/orders/poll")
@login_required
@admin_required
def poll_orders():
    status = request.args.get("status", "").strip()
    search = request.args.get("q", "").strip()

    query = Order.query.filter_by(is_deleted=False).order_by(Order.created_at.desc())

    if status and status in Order.STATUSES:
        query = query.filter_by(status=status)

    if search:
        try:
            oid   = int(search.lstrip("#"))
            query = query.filter(Order.id == oid)
        except ValueError:
            query = query.join(User).filter(User.name.ilike(f"%{search}%"))

    orders  = query.all()
    payload = []
    for o in orders:
        payload.append({
            "id":         o.id,
            "customer":   o.user.name,
            "email":      o.user.email,
            "item_count": o.item_count,
            "total":      round(float(o.total_float), 2),
            "status":     o.status,
            "created_at": o.created_at.strftime("%b %d, %Y"),
        })

    return jsonify({"success": True, "orders": payload})


@admin_bp.route("/api/orders/<int:order_id>/status")
@login_required
@admin_required
def poll_order_status(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"success": False, "message": "Order not found"}), 404
    return jsonify({"success": True, "id": order.id, "status": order.status})


# ─────────────────────────────────────────────────────────────
# PRODUCTS LIST
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/products")
@login_required
@admin_required
def products():
    category = request.args.get("category", "")
    search   = request.args.get("q", "")
    query    = Product.query

    if category and category in Product.CATEGORIES:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    all_products = query.order_by(Product.created_at.desc()).all()
    return render_template(
        "admin.html",
        view             = "products",
        products         = all_products,
        categories       = Product.CATEGORIES,
        current_category = category,
        search           = search,
        title            = "Manage Products – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# ADD PRODUCT  (supports image_url_2, image_url_3)
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
        image_url_2 = request.form.get("image_url_2", "").strip() or None
        image_url_3 = request.form.get("image_url_3", "").strip() or None

        errors = []
        if not name:        errors.append("Product name is required.")
        if not description: errors.append("Description is required.")
        if not price:       errors.append("Price is required.")
        if not category:    errors.append("Category is required.")
        if not image_url:   errors.append("Primary image URL is required.")
        if category and category not in Product.CATEGORIES:
            errors.append("Invalid category.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return redirect(url_for("admin.add_product"))

        try:
            product = Product(
                name        = name,
                description = description,
                price       = float(price),
                stock       = int(stock),
                category    = category,
                image_url   = image_url,
                image_url_2 = image_url_2,
                image_url_3 = image_url_3,
            )
            db.session.add(product)
            db.session.commit()
            flash(f'✅ Product "{name}" added successfully!', "success")
            return redirect(url_for("admin.products"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding product: {str(e)}", "danger")
            return redirect(url_for("admin.add_product"))

    return render_template(
        "admin.html",
        view       = "add_product",
        categories = Product.CATEGORIES,
        title      = "Add Product – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# EDIT PRODUCT  (supports image_url_2, image_url_3)
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/products/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("admin.products"))

    if request.method == "POST":
        product.name        = request.form.get("name", "").strip()
        product.description = request.form.get("description", "").strip()
        product.price       = float(request.form.get("price", 0))
        product.stock       = int(request.form.get("stock", 0))
        product.category    = request.form.get("category", "")
        product.image_url   = request.form.get("image_url", "").strip()
        product.image_url_2 = request.form.get("image_url_2", "").strip() or None
        product.image_url_3 = request.form.get("image_url_3", "").strip() or None

        try:
            db.session.commit()
            flash(f'✅ Product "{product.name}" updated!', "success")
            return redirect(url_for("admin.products"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating product: {str(e)}", "danger")

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
    product = db.session.get(Product, product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("admin.products"))

    name = product.name
    try:
        db.session.delete(product)
        db.session.commit()
        flash(f'🗑️ Product "{name}" deleted.', "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Cannot delete – product may have order history. Error: {str(e)}", "danger")

    return redirect(url_for("admin.products"))


# ─────────────────────────────────────────────────────────────
# QUICK STOCK UPDATE (AJAX)
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/products/stock", methods=["POST"])
@login_required
@admin_required
def update_stock():
    data       = request.get_json()
    product_id = data.get("product_id")
    new_stock  = data.get("stock")

    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404

    try:
        product.stock = int(new_stock)
        db.session.commit()
        return jsonify({"success": True, "stock": product.stock})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# ORDERS LIST
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/orders")
@login_required
@admin_required
def orders():
    status = request.args.get("status", "")
    search = request.args.get("q", "")
    query  = Order.query.filter_by(is_deleted=False).order_by(Order.created_at.desc())

    if status and status in Order.STATUSES:
        query = query.filter_by(status=status)

    if search:
        try:
            oid   = int(search.lstrip("#"))
            query = query.filter(Order.id == oid)
        except ValueError:
            query = query.join(User).filter(User.name.ilike(f"%{search}%"))

    all_orders = query.all()
    return render_template(
        "admin.html",
        view              = "orders",
        orders            = all_orders,
        current_status    = status,
        statuses          = Order.STATUSES,
        search            = search,
        deletable_statuses = DELETABLE_STATUSES,
        title             = "Manage Orders – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# ORDER DETAIL
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/orders/<int:order_id>")
@login_required
@admin_required
def order_detail(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("admin.orders"))

    return render_template(
        "admin.html",
        view     = "order_detail",
        order    = order,
        statuses = Order.STATUSES,
        title    = f"Order #{order_id:04d} – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# UPDATE ORDER STATUS  (sends email notification automatically)
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@login_required
@admin_required
def update_order_status(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("admin.orders"))

    if order.status in TERMINAL_STATUSES:
        flash(
            f"⛔ Order #{order_id:04d} is already "
            f"'{order.status.replace('_', ' ').title()}' and cannot be changed.",
            "danger"
        )
        if request.form.get("from") == "detail":
            return redirect(url_for("admin.order_detail", order_id=order_id))
        return redirect(url_for("admin.orders"))

    new_status = request.form.get("status")
    if new_status not in Order.STATUSES:
        flash("Invalid status.", "danger")
        return redirect(url_for("admin.orders"))

    old_status   = order.status
    order.status = new_status

    if new_status == "failed_to_deliver" and old_status != "failed_to_deliver":
        reason = request.form.get("fail_reason", "").strip()
        order.cancel_reason = reason or "Failed to deliver – marked by admin"
        for item in order.items:
            item.product.stock += item.quantity

    db.session.commit()
    flash(f"✅ Order #{order_id:04d} updated to '{new_status}'.", "success")

    # ── Email notification ────────────────────────────────────
    if old_status != new_status:
        try:
            from email_utils import send_order_status_update
            send_order_status_update(
                user       = order.user,
                order      = order,
                new_status = new_status
            )
            logger.info(f"Status-update email sent for order #{order_id} → {new_status}")
        except Exception as e:
            logger.warning(f"Status email failed for order #{order_id}: {e}")

    if request.form.get("from") == "detail":
        return redirect(url_for("admin.order_detail", order_id=order_id))
    return redirect(url_for("admin.orders"))


# ─────────────────────────────────────────────────────────────
# SOFT-DELETE ORDER  (hide from dashboard/orders list)
# Database values (revenue, counts) are NOT changed.
# Only paid or delivered orders may be hidden.
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/orders/<int:order_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_order(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("admin.orders"))

    if order.status not in DELETABLE_STATUSES:
        flash(
            f"⛔ Only paid or delivered orders can be removed from view. "
            f"This order is '{order.status.replace('_', ' ').title()}'.",
            "danger"
        )
        return redirect(url_for("admin.orders"))

    order.is_deleted = True
    db.session.commit()
    flash(f"🗑️ Order #{order_id:04d} has been removed from the list.", "success")

    # Redirect to dashboard if the request came from there
    if request.form.get("from") == "dashboard":
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("admin.orders"))


# ─────────────────────────────────────────────────────────────
# CUSTOMERS / USERS LIST  (FIX: robust, uses order_counts dict)
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/users")
@login_required
@admin_required
def users():
    try:
        all_users = User.query.order_by(User.created_at.desc()).all()

        from sqlalchemy import func
        order_counts = dict(
            db.session.query(Order.user_id, func.count(Order.id))
            .group_by(Order.user_id).all()
        )

        # Build per-user spend totals for richer UI
        spend_totals = dict(
            db.session.query(Order.user_id, func.sum(Order.total_price))
            .filter(Order.status != "pending")
            .group_by(Order.user_id).all()
        )

        return render_template(
            "admin.html",
            view         = "users",
            users        = all_users,
            order_counts = order_counts,
            spend_totals = spend_totals,
            title        = "Manage Customers – GadgetHub PH"
        )
    except Exception as e:
        logger.error(f"Customers page error: {e}", exc_info=True)
        flash(f"Error loading customers: {str(e)}", "danger")
        return redirect(url_for("admin.dashboard"))


# ─────────────────────────────────────────────────────────────
# TOGGLE ADMIN
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@login_required
@admin_required
def toggle_admin(user_id):
    user = db.session.get(User, user_id)
    if not user or user.id == current_user.id:
        flash("Cannot modify this user.", "danger")
        return redirect(url_for("admin.users"))

    user.is_admin = not user.is_admin
    db.session.commit()
    role = "admin" if user.is_admin else "customer"
    flash(f"✅ {user.name} is now a {role}.", "success")
    return redirect(url_for("admin.users"))


# ─────────────────────────────────────────────────────────────
# REVIEWS MANAGEMENT
# ─────────────────────────────────────────────────────────────

@admin_bp.route("/reviews")
@login_required
@admin_required
def reviews():
    all_reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template(
        "admin.html",
        view    = "reviews",
        reviews = all_reviews,
        title   = "Manage Reviews – GadgetHub PH"
    )


@admin_bp.route("/reviews/<int:review_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_review(review_id):
    review = db.session.get(Review, review_id)
    if review:
        db.session.delete(review)
        db.session.commit()
        flash("Review deleted.", "success")
    return redirect(url_for("admin.reviews"))