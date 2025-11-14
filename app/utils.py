"""Helper utilities: decorators, serialization, and cart helpers."""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import abort, session
from flask_login import current_user, login_required


def role_required(*roles: str) -> Callable:
    """Ensure the current user has one of the required roles."""

    if not roles:
        raise ValueError("At least one role must be provided")

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def serialize_user(user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "phone": user.phone,
        "preferences": user.preferences,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def serialize_note(note) -> dict:
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "tags": note.tags,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }


def serialize_feedback(feedback) -> dict:
    return {
        "id": feedback.id,
        "message": feedback.message,
        "rating": feedback.rating,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
        "user": feedback.author.name if feedback.author else "Гость",
    }


def serialize_order(order) -> dict:
    return {
        "id": order.id,
        "user_id": order.user_id,
        "total": order.total,
        "status": order.status,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "items": [
            {
                "product_id": item.product_id,
                "product_name": item.product.name if item.product else None,
                "quantity": item.quantity,
                "price": item.price,
            }
            for item in order.items
        ],
    }


def get_cart() -> list[dict]:
    cart = session.get("cart", [])
    if not isinstance(cart, list):
        cart = []
    session["cart"] = cart
    return cart


def clear_cart() -> None:
    session["cart"] = []


def add_to_cart(product_id: int, quantity: int = 1) -> None:
    cart = get_cart()
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            break
    else:
        cart.append({"product_id": product_id, "quantity": quantity})
    session.modified = True