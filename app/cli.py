"""Custom Flask CLI commands for database initialization and seeding."""

from __future__ import annotations

import click

from . import bcrypt, db
from .models import Feedback, Note, Order, OrderItem, Product, User


def register_cli(app):
    """Attach custom commands to the Flask CLI."""

    @app.cli.command("init-db")
    def init_db_command():
        """Create all database tables."""
        with app.app_context():
            db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("seed-db")
    def seed_db_command():
        """Populate the database with demo data."""
        with app.app_context():
            _seed_database()
        click.echo("Demo data inserted.")


def _seed_database():
    # Ensure tables exist
    db.create_all()

    if User.query.first():
        click.echo("Database already has data; skipping seeding.")
        return

    admin = User(
        email="admin@example.com",
        password_hash=bcrypt.generate_password_hash("Admin123!").decode("utf-8"),
        role="admin",
        name="Администратор",
        phone="+7 999 000 00 00",
        preferences="{\"theme\": \"dark\", \"language\": \"ru\"}",
    )
    user = User(
        email="user@example.com",
        password_hash=bcrypt.generate_password_hash("User123!").decode("utf-8"),
        role="user",
        name="Мария",
        phone="+7 999 111 22 33",
        preferences="{\"theme\": \"light\", \"language\": \"ru\"}",
    )
    db.session.add_all([admin, user])
    db.session.flush()

    notes = [
        Note(user_id=user.id, title="Список покупок", content="Молоко, хлеб, сыр", tags="дом"),
        Note(user_id=user.id, title="Идеи для блога", content="Фичи приложения блокнот", tags="работа"),
        Note(user_id=admin.id, title="План релиза", content="Запустить новую версию", tags="админ"),
    ]
    db.session.add_all(notes)

    products = [
        Product(name="Мини-блокнот", category="Канцелярия", price=350.0, stock=50, description="Компактный блокнот", tags="блокнот,мини"),
        Product(name="Перьевая ручка", category="Письменные принадлежности", price=1200.0, stock=20, description="Элегантная ручка", tags="ручка,подарок"),
        Product(name="Наклейки", category="Аксессуары", price=150.0, stock=200, description="Набор вдохновляющих наклеек", tags="наклейки,декор"),
    ]
    db.session.add_all(products)
    db.session.flush()

    feedback_entries = [
        Feedback(user_id=user.id, message="Очень удобно вести заметки и покупки!", rating=5),
        Feedback(user_id=None, message="Хотелось бы больше тем оформления", rating=4),
    ]
    db.session.add_all(feedback_entries)

    order = Order(user_id=user.id, total=1550.0, status="paid")
    db.session.add(order)
    db.session.flush()

    order_items = [
        OrderItem(order_id=order.id, product_id=products[0].id, quantity=1, price=350.0),
        OrderItem(order_id=order.id, product_id=products[1].id, quantity=1, price=1200.0),
    ]
    db.session.add_all(order_items)

    db.session.commit()
