"""
routes/orders.py – GadgetHub PH
=================================
Orders blueprint: checkout, order history, order detail, review submission.
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, CartItem, Order, OrderItem, Review

orders_bp = Blueprint("orders", __name__, url_prefix="/orders")


# ─────────────────────────────────────────────────────────────
# CHECKOUT PAGE
# ─────────────────────────────────────────────────────────────

@orders_bp.route("/checkout")
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        flash("Your cart is empty!", "warning")
        return redirect(url_for("cart.view_cart"))

    cart_total = sum(item.subtotal for item in cart_items)

    return render_template(
        "checkout.html",
        cart_items = cart_items,
        cart_total = cart_total,
        title      = "Checkout – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# PLACE ORDER (POST from checkout.js)
# ─────────────────────────────────────────────────────────────

@orders_bp.route("/checkout", methods=["POST"])
@login_required
def place_order():
    data             = request.get_json()
    shipping_address = data.get("shipping_address", "").strip()

    if not shipping_address:
        return jsonify({"success": False, "message": "Shipping address is required."}), 400

    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        return jsonify({"success": False, "message": "Your cart is empty."}), 400

    # Calculate total
    total = sum(item.subtotal for item in cart_items)

    # Create order
    order = Order(
        user_id          = current_user.id,
        total_price      = total,
        status           = "pending",
        shipping_address = shipping_address
    )
    db.session.add(order)
    db.session.flush()  # get order.id before commit

    # Create order items & reduce stock
    created_items = []
    for item in cart_items:
        order_item = OrderItem(
            order_id   = order.id,
            product_id = item.product_id,
            quantity   = item.quantity,
            unit_price = item.product.price
        )
        db.session.add(order_item)
        created_items.append(order_item)

        # Reduce stock
        item.product.stock -= item.quantity

    # Clear cart
    CartItem.query.filter_by(user_id=current_user.id).delete()

    db.session.commit()

    # ── Send order confirmation email (non-blocking) ──────────
    try:
        from email_utils import send_order_confirmation

        # Re-fetch order items with product relationship loaded
        final_items = OrderItem.query.filter_by(order_id=order.id).all()
        send_order_confirmation(
            user        = current_user,
            order       = order,
            order_items = final_items
        )
    except Exception as e:
        # Email failure must NEVER break the order — just log it
        import logging
        logging.getLogger(__name__).warning(
            f"Order #{order.id} confirmation email failed: {e}"
        )

    return jsonify({
        "success":  True,
        "order_id": order.id,
        "message":  "Order placed successfully!"
    })


# ─────────────────────────────────────────────────────────────
# ORDER HISTORY
# ─────────────────────────────────────────────────────────────

@orders_bp.route("/")
@login_required
def order_history():
    orders = Order.query.filter_by(
        user_id=current_user.id
    ).order_by(Order.created_at.desc()).all()

    return render_template(
        "order.html",
        orders = orders,
        order  = None,
        title  = "My Orders – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# ORDER DETAIL
# ─────────────────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.filter_by(
        id      = order_id,
        user_id = current_user.id
    ).first_or_404()

    return render_template(
        "order.html",
        order  = order,
        orders = None,
        title  = f"Order #{order_id:04d} – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# SUBMIT REVIEW  (POST /orders/<id>/review)
# ─────────────────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>/review", methods=["POST"])
@login_required
def submit_review(order_id):
    order = Order.query.filter_by(
        id      = order_id,
        user_id = current_user.id
    ).first_or_404()

    data       = request.get_json()
    product_id = data.get("product_id")
    comment    = data.get("comment", "").strip()

    try:
        rating = int(data.get("rating", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid rating value."}), 400

    if not (1 <= rating <= 5):
        return jsonify({"success": False, "message": "Rating must be between 1 and 5."}), 400

    item = next((i for i in order.items if i.product_id == product_id), None)
    if not item:
        return jsonify({"success": False, "message": "Product not in this order."}), 400

    existing = Review.query.filter_by(
        user_id    = current_user.id,
        product_id = product_id
    ).first()

    if existing:
        existing.rating  = rating
        existing.comment = comment
    else:
        review = Review(
            user_id    = current_user.id,
            product_id = product_id,
            rating     = rating,
            comment    = comment
        )
        db.session.add(review)

    db.session.commit()
    return jsonify({"success": True, "message": "Review submitted!"})