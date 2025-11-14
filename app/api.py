"""REST API endpoints for authentication, notes, shop, search, and admin tools."""

from __future__ import annotations

import json
from typing import Any

from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required, login_user, logout_user

from . import bcrypt, db
from .models import Feedback, Note, Order, OrderItem, Product, User
from .utils import (
    add_to_cart,
    clear_cart,
    get_cart,
    role_required,
    serialize_feedback,
    serialize_note,
    serialize_order,
    serialize_user,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _payload() -> dict[str, Any]:
    if request.is_json:
        data = request.get_json(silent=True)
        if isinstance(data, dict):
            return data
        return {}
    return request.form.to_dict()


# -----------------
# Auth endpoints
# -----------------


@api_bp.post("/auth/register")
def register_user():
    data = _payload()
    email = data.get("email", "").lower().strip()
    password = data.get("password", "")
    name = data.get("name", "")
    phone = data.get("phone", "")

    errors: dict[str, str] = {}

    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError as exc:
        errors["email"] = str(exc)

    if len(password) < 8:
        errors["password"] = "Пароль должен быть не короче 8 символов"

    if User.query.filter_by(email=email).first():
        errors["email"] = "Пользователь с таким email уже существует"

    if errors:
        return jsonify({"errors": errors}), 400

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(email=email, password_hash=password_hash, name=name, phone=phone)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return jsonify({"message": "Регистрация успешна", "user": serialize_user(user)})


@api_bp.post("/auth/login")
def login():
    data = _payload()
    email = data.get("email", "").lower().strip()
    password = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Неверный email или пароль"}), 401

    login_user(user)
    return jsonify({"message": "Вход выполнен", "user": serialize_user(user)})


@api_bp.post("/auth/logout")
@login_required
def logout():
    logout_user()
    clear_cart()
    return jsonify({"message": "Вы вышли из системы"})


@api_bp.get("/auth/me")
@login_required
def auth_me():
    return jsonify({"user": serialize_user(current_user)})


@api_bp.put("/auth/profile")
@login_required
def update_profile():
    data = _payload()
    current_user.name = data.get("name", current_user.name)
    current_user.phone = data.get("phone", current_user.phone)
    db.session.commit()
    return jsonify({"message": "Профиль обновлён", "user": serialize_user(current_user)})


@api_bp.put("/auth/preferences")
@login_required
def update_preferences():
    data = _payload()
    prefs = data.get("preferences", {})
    if isinstance(prefs, str):
        pref_json = prefs
    else:
        try:
            pref_json = json.dumps(prefs)
        except (TypeError, ValueError):
            return jsonify({"error": "Неверный формат настроек"}), 400

    current_user.preferences = pref_json
    db.session.commit()
    return jsonify({"message": "Предпочтения сохранены"})


@api_bp.put("/auth/password")
@login_required
def change_password():
    data = _payload()
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not bcrypt.check_password_hash(current_user.password_hash, current_password):
        return jsonify({"error": "Текущий пароль неверен"}), 400

    if len(new_password) < 8:
        return jsonify({"error": "Новый пароль слишком короткий"}), 400

    current_user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()
    return jsonify({"message": "Пароль обновлён"})


# -----------------
# Notes CRUD
# -----------------


@api_bp.get("/notes")
@login_required
def list_notes():
    query = Note.query.filter_by(user_id=current_user.id).order_by(Note.updated_at.desc())
    q = request.args.get("q")
    if q:
        like = f"%{q}%"
        query = query.filter((Note.title.ilike(like)) | (Note.content.ilike(like)) | (Note.tags.ilike(like)))
    notes = [serialize_note(note) for note in query.all()]
    return jsonify({"notes": notes})


@api_bp.post("/notes")
@login_required
def create_note():
    data = _payload()
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()

    if not title or not content:
        return jsonify({"error": "Заголовок и текст обязательны"}), 400

    note = Note(user_id=current_user.id, title=title, content=content, tags=data.get("tags"))
    db.session.add(note)
    db.session.commit()
    return jsonify({"message": "Заметка создана", "note": serialize_note(note)}), 201


@api_bp.put("/notes/<int:note_id>")
@login_required
def update_note(note_id: int):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id and current_user.role != "admin":
        return jsonify({"error": "Нет доступа"}), 403

    data = _payload()
    note.title = data.get("title", note.title)
    note.content = data.get("content", note.content)
    note.tags = data.get("tags", note.tags)
    db.session.commit()
    return jsonify({"message": "Заметка обновлена", "note": serialize_note(note)})


@api_bp.delete("/notes/<int:note_id>")
@login_required
def delete_note(note_id: int):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id and current_user.role != "admin":
        return jsonify({"error": "Нет доступа"}), 403

    db.session.delete(note)
    db.session.commit()
    return jsonify({"message": "Заметка удалена"})


# -----------------
# Feedback & search
# -----------------


@api_bp.post("/feedback")
def submit_feedback():
    data = _payload()
    message = data.get("message", "").strip()
    rating = data.get("rating")

    if not message:
        return jsonify({"error": "Сообщение не может быть пустым"}), 400

    entry = Feedback(
        user_id=current_user.id if current_user.is_authenticated else None,
        message=message,
        rating=int(rating) if rating else None,
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({"message": "Спасибо за обратную связь!"})


@api_bp.get("/feedback")
@role_required("admin")
def list_feedback():
    entries = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return jsonify({"feedback": [serialize_feedback(item) for item in entries]})


@api_bp.get("/search")
@login_required
def search():
    term = request.args.get("q", "").strip()
    like = f"%{term}%" if term else "%"

    notes_query = Note.query.filter_by(user_id=current_user.id)
    if term:
        notes_query = notes_query.filter(
            (Note.title.ilike(like)) | (Note.content.ilike(like)) | (Note.tags.ilike(like))
        )
    notes = [serialize_note(n) for n in notes_query.limit(20).all()]

    product_query = Product.query
    if term:
        product_query = product_query.filter(
            (Product.name.ilike(like)) | (Product.description.ilike(like)) | (Product.tags.ilike(like))
        )
    products = [product.to_dict() for product in product_query.limit(20).all()]

    return jsonify({"notes": notes, "products": products})


# -----------------
# Shop and cart
# -----------------


@api_bp.get("/products")
def list_products():
    query = Product.query
    category = request.args.get("category")
    if category:
        query = query.filter(Product.category == category)

    search_term = request.args.get("q")
    if search_term:
        like = f"%{search_term}%"
        query = query.filter(
            (Product.name.ilike(like)) | (Product.description.ilike(like)) | (Product.tags.ilike(like))
        )

    max_price = request.args.get("max_price")
    if max_price:
        try:
            price_value = float(max_price)
            query = query.filter(Product.price <= price_value)
        except ValueError:
            pass

    products = [product.to_dict() for product in query.order_by(Product.name).all()]
    return jsonify({"products": products})


@api_bp.get("/cart")
@login_required
def get_cart_items():
    cart = get_cart()
    detailed = []
    total = 0.0
    for item in cart:
        product = Product.query.get(item["product_id"])
        if not product:
            continue
        subtotal = product.price * item["quantity"]
        total += subtotal
        detailed.append(
            {
                "product": product.to_dict(),
                "quantity": item["quantity"],
                "subtotal": subtotal,
            }
        )
    return jsonify({"items": detailed, "total": total})


@api_bp.post("/cart")
@login_required
def add_cart_item():
    data = _payload()
    try:
        product_id = int(data.get("product_id"))
        quantity = int(data.get("quantity", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "Неверные данные"}), 400

    if quantity <= 0:
        return jsonify({"error": "Количество должно быть положительным"}), 400

    product = Product.query.get_or_404(product_id)
    if product.stock < quantity:
        return jsonify({"error": "Недостаточно товара на складе"}), 400

    add_to_cart(product_id, quantity)
    return jsonify({"message": "Товар добавлен в корзину"})


@api_bp.delete("/cart/<int:product_id>")
@login_required
def remove_cart_item(product_id: int):
    cart = get_cart()
    new_cart = [item for item in cart if item["product_id"] != product_id]
    session_changed = new_cart != cart
    if session_changed:
        session["cart"] = new_cart
        session.modified = True
    return jsonify({"message": "Товар удалён"})


@api_bp.post("/cart/clear")
@login_required
def clear_cart_route():
    clear_cart()
    return jsonify({"message": "Корзина очищена"})


@api_bp.post("/checkout")
@login_required
def checkout():
    cart = get_cart()
    if not cart:
        return jsonify({"error": "Корзина пуста"}), 400

    prepared_items: list[tuple[Product, int]] = []
    total = 0.0
    for item in cart:
        product = Product.query.get(item["product_id"])
        if not product:
            continue
        qty = item["quantity"]
        if product.stock < qty:
            return jsonify({"error": f"Недостаточно товара: {product.name}"}), 400
        prepared_items.append((product, qty))
        total += product.price * qty

    if not prepared_items:
        return jsonify({"error": "Нет доступных товаров"}), 400

    order = Order(user_id=current_user.id, total=total, status="paid")
    db.session.add(order)
    db.session.flush()

    for product, qty in prepared_items:
        product.stock -= qty
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=qty,
                price=product.price,
            )
        )

    db.session.commit()
    clear_cart()
    return jsonify({"message": "Заказ оформлен", "order": serialize_order(order)})


# -----------------
# Admin endpoints
# -----------------


@api_bp.get("/admin/users")
@role_required("admin")
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({"users": [serialize_user(u) for u in users]})


@api_bp.get("/admin/orders")
@role_required("admin")
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return jsonify({"orders": [serialize_order(o) for o in orders]})
