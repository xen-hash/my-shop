"""
routes/orders.py – GadgetHub PH
=================================
Orders blueprint: checkout, order history, order detail.
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, CartItem, Order, OrderItem

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
    for item in cart_items:
        order_item = OrderItem(
            order_id   = order.id,
            product_id = item.product_id,
            quantity   = item.quantity,
            unit_price = item.product.price
        )
        db.session.add(order_item)

        # Reduce stock
        item.product.stock -= item.quantity

    # Clear cart
    CartItem.query.filter_by(user_id=current_user.id).delete()

    db.session.commit()

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