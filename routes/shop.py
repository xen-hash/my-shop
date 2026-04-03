"""
routes/shop.py – GadgetHub PH
==============================
Shop blueprint: homepage, product listing, product detail, search.
FIXED: Simple 60-second in-memory cache for featured products.
       No extra dependencies needed — pure Python.
"""

import time
from flask import Blueprint, render_template, request
from models import Product

shop_bp = Blueprint("shop", __name__)

# ── Simple in-memory cache (no extra library needed) ─────────
_featured_cache = {"data": None, "expires": 0}

def get_featured_products():
    """Return up to 4 in-stock products. Re-queries DB at most once per 60s."""
    now = time.time()
    if _featured_cache["data"] and now < _featured_cache["expires"]:
        return _featured_cache["data"]
    result = Product.query.filter(Product.stock > 0).limit(4).all()
    _featured_cache["data"]    = result
    _featured_cache["expires"] = now + 60
    return result


# ─────────────────────────────────────────────────────────────
# HOME / PRODUCT LISTING
# ─────────────────────────────────────────────────────────────

@shop_bp.route("/")
def index():
    category = request.args.get("category", "").strip().lower()
    search   = request.args.get("q", "").strip()
    page     = request.args.get("page", 1, type=int)

    query = Product.query

    if category and category in Product.CATEGORIES:
        query = query.filter_by(category=category)

    if search:
        query = query.filter(
            Product.name.ilike(f"%{search}%") |
            Product.description.ilike(f"%{search}%")
        )

    products   = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=12, error_out=False
    )
    categories = Product.CATEGORIES
    featured   = get_featured_products()

    return render_template(
        "index.html",
        products=products,
        categories=categories,
        featured=featured,
        current_category=category,
        search=search,
        title="GadgetHub PH – Tech Accessories"
    )


# ─────────────────────────────────────────────────────────────
# PRODUCT DETAIL
# ─────────────────────────────────────────────────────────────

@shop_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related = Product.query.filter(
        Product.category == product.category,
        Product.id       != product.id
    ).limit(4).all()

    return render_template(
        "product.html",
        product=product,
        related=related,
        title=f"{product.name} – GadgetHub PH"
    )