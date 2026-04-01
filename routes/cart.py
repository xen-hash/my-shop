"""
routes/cart.py – GadgetHub PH
==============================
Cart blueprint: add, update, remove cart items.
All routes return JSON for use with fetch() in the frontend.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, CartItem, Product

cart_bp = Blueprint("cart", __name__, url_prefix="/cart")


# ─────────────────────────────────────────────────────────────
# VIEW CART
# ─────────────────────────────────────────────────────────────

@cart_bp.route("/")
@login_required
def view_cart():
    from flask import render_template
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    cart_total = sum(item.subtotal for item in cart_items)
    return render_template(
        "cart.html",
        cart_items=cart_items,
        cart_total=cart_total,
        title="My Cart – GadgetHub PH"
    )


# ─────────────────────────────────────────────────────────────
# ADD TO CART
# ─────────────────────────────────────────────────────────────

@cart_bp.route("/add", methods=["POST"])
@login_required
def add_to_cart():
    data       = request.get_json()
    product_id = data.get("product_id")
    quantity   = int(data.get("quantity", 1))

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"success": False, "message": "Product not found."}), 404

    if product.stock == 0:
        return jsonify({"success": False, "message": "This product is out of stock."}), 400

    # Check if already in cart
    item = CartItem.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()

    if item:
        new_qty = item.quantity + quantity
        if new_qty > product.stock:
            new_qty = product.stock
        item.quantity = new_qty
    else:
        item = CartItem(
            user_id    = current_user.id,
            product_id = product_id,
            quantity   = min(quantity, product.stock)
        )
        db.session.add(item)

    db.session.commit()

    return jsonify({
        "success":    True,
        "message":    f"{product.name} added to cart!",
        "cart_count": current_user.cart_count
    })


# ─────────────────────────────────────────────────────────────
# UPDATE QUANTITY
# ─────────────────────────────────────────────────────────────

@cart_bp.route("/update", methods=["POST"])
@login_required
def update_cart():
    data         = request.get_json()
    cart_item_id = data.get("cart_item_id")
    quantity     = int(data.get("quantity", 1))

    item = CartItem.query.filter_by(
        id      = cart_item_id,
        user_id = current_user.id
    ).first()

    if not item:
        return jsonify({"success": False, "message": "Item not found."}), 404

    if quantity < 1:
        db.session.delete(item)
        db.session.commit()
        return jsonify({
            "success":    True,
            "removed":    True,
            "cart_total": current_user.cart_total,
            "cart_count": current_user.cart_count
        })

    if quantity > item.product.stock:
        quantity = item.product.stock

    item.quantity = quantity
    db.session.commit()

    return jsonify({
        "success":    True,
        "subtotal":   item.subtotal,
        "cart_total": current_user.cart_total,
        "cart_count": current_user.cart_count
    })


# ─────────────────────────────────────────────────────────────
# REMOVE ITEM
# ─────────────────────────────────────────────────────────────

@cart_bp.route("/remove", methods=["POST"])
@login_required
def remove_from_cart():
    data         = request.get_json()
    cart_item_id = data.get("cart_item_id")

    item = CartItem.query.filter_by(
        id      = cart_item_id,
        user_id = current_user.id
    ).first()

    if not item:
        return jsonify({"success": False, "message": "Item not found."}), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({
        "success":    True,
        "cart_total": current_user.cart_total,
        "cart_count": current_user.cart_count
    })