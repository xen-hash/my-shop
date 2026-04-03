"""
routes/orders.py – GadgetHub PH
=================================
Orders blueprint: checkout, order history, order detail,
cancel order, review submission.
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, CartItem, Order, OrderItem, Review
import logging

orders_bp = Blueprint("orders", __name__, url_prefix="/orders")
logger = logging.getLogger(__name__)

# Statuses where customer is still allowed to cancel
CANCELLABLE_STATUSES = ["pending", "confirmed", "order_received"]

# Statuses that are terminal — no further changes allowed
TERMINAL_STATUSES = ["cancelled", "paid", "failed_to_deliver"]


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
# PLACE ORDER
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

    # Only place order for in-stock items
    valid_items = [item for item in cart_items if item.product.stock > 0]
    if not valid_items:
        return jsonify({"success": False, "message": "All items in your cart are out of stock."}), 400

    total = sum(item.subtotal for item in valid_items)

    order = Order(
        user_id          = current_user.id,
        total_price      = total,
        status           = "pending",
        shipping_address = shipping_address
    )
    db.session.add(order)
    db.session.flush()

    for item in valid_items:
        order_item = OrderItem(
            order_id   = order.id,
            product_id = item.product_id,
            quantity   = item.quantity,
            unit_price = item.product.price
        )
        db.session.add(order_item)
        item.product.stock -= item.quantity

    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    # Send confirmation email
    try:
        from email_utils import send_order_confirmation
        final_items = OrderItem.query.filter_by(order_id=order.id).all()
        send_order_confirmation(
            user        = current_user,
            order       = order,
            order_items = final_items
        )
        logger.info(f"Confirmation email sent for order #{order.id} to {current_user.email}")
    except Exception as e:
        logger.warning(f"Order #{order.id} confirmation email failed: {e}")

    return jsonify({
        "success":  True,
        "order_id": order.id,
        "message":  "Order placed successfully!"
    })


# ─────────────────────────────────────────────────────────────
# CANCEL ORDER
# ─────────────────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    order = Order.query.filter_by(
        id      = order_id,
        user_id = current_user.id
    ).first_or_404()

    # Check if cancellable
    if order.status not in CANCELLABLE_STATUSES:
        return jsonify({
            "success": False,
            "message": f"This order cannot be cancelled. It is already '{order.status.replace('_', ' ').title()}'."
        }), 400

    data   = request.get_json()
    reason = data.get("reason", "").strip()

    if not reason:
        return jsonify({"success": False, "message": "Please provide a reason for cancellation."}), 400

    # Restore stock
    for item in order.items:
        item.product.stock += item.quantity

    old_status    = order.status
    order.status  = "cancelled"
    order.cancel_reason = reason
    db.session.commit()

    # Send cancellation email
    try:
        from email_utils import send_order_cancellation
        send_order_cancellation(
            user   = current_user,
            order  = order,
            reason = reason
        )
        logger.info(f"Cancellation email sent for order #{order.id}")
    except Exception as e:
        logger.warning(f"Cancellation email failed for order #{order.id}: {e}")

    return jsonify({
        "success": True,
        "message": "Your order has been cancelled successfully."
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
        orders              = orders,
        order               = None,
        cancellable_statuses = CANCELLABLE_STATUSES,
        title               = "My Orders – GadgetHub PH"
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
        order                = order,
        orders               = None,
        cancellable_statuses = CANCELLABLE_STATUSES,
        title                = f"Order #{order_id:04d} – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# SUBMIT REVIEW
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
        db.session.add(Review(
            user_id    = current_user.id,
            product_id = product_id,
            rating     = rating,
            comment    = comment
        ))

    db.session.commit()
    return jsonify({"success": True, "message": "Review submitted!"})