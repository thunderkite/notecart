"""Basic smoke tests for the NoteCart application."""

import pytest

from app import create_app, db
from app.models import User


@pytest.fixture
def app():
    """Create application instance for testing."""
    test_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "test-secret",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLI test runner."""
    return app.test_cli_runner()


def test_health_check(client):
    """Ensure /health returns OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_register_user(client):
    """Test user registration endpoint."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePass123",
            "name": "Test User",
        },
    )
    assert response.status_code == 200
    data = response.json
    assert data["message"] == "Регистрация успешна"
    assert data["user"]["email"] == "test@example.com"


def test_login_user(client, app):
    """Test user login with correct credentials."""
    with app.app_context():
        from app import bcrypt

        user = User(
            email="login@example.com",
            password_hash=bcrypt.generate_password_hash("TestPass123").decode("utf-8"),
            name="Login Test",
        )
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "TestPass123"},
    )
    assert response.status_code == 200
    assert response.json["message"] == "Вход выполнен"


def test_create_note(client, app):
    """Test creating a note for authenticated user."""
    with app.app_context():
        from app import bcrypt

        user = User(
            email="notes@example.com",
            password_hash=bcrypt.generate_password_hash("Pass123").decode("utf-8"),
        )
        db.session.add(user)
        db.session.commit()

    # Login
    client.post(
        "/api/auth/login", json={"email": "notes@example.com", "password": "Pass123"}
    )

    # Create note
    response = client.post(
        "/api/notes", json={"title": "Test Note", "content": "Note content"}
    )
    assert response.status_code == 201
    assert response.json["message"] == "Заметка создана"
    assert response.json["note"]["title"] == "Test Note"


def test_list_products(client):
    """Test product listing endpoint."""
    response = client.get("/api/products")
    assert response.status_code == 200
    assert "products" in response.json


def test_add_to_cart(client, app):
    """Test adding product to cart."""
    with app.app_context():
        from app import bcrypt
        from app.models import Product

        user = User(
            email="cart@example.com",
            password_hash=bcrypt.generate_password_hash("Pass123").decode("utf-8"),
        )
        product = Product(
            name="Test Product", price=100.0, stock=10, category="Test"
        )
        db.session.add_all([user, product])
        db.session.commit()
        product_id = product.id

    # Login
    client.post(
        "/api/auth/login", json={"email": "cart@example.com", "password": "Pass123"}
    )

    # Add to cart
    response = client.post(
        "/api/cart", json={"product_id": product_id, "quantity": 2}
    )
    assert response.status_code == 200
    assert response.json["message"] == "Товар добавлен в корзину"


def test_checkout(client, app):
    """Test checkout process."""
    with app.app_context():
        from app import bcrypt
        from app.models import Product

        user = User(
            email="checkout@example.com",
            password_hash=bcrypt.generate_password_hash("Pass123").decode("utf-8"),
        )
        product = Product(
            name="Checkout Product", price=50.0, stock=5, category="Test"
        )
        db.session.add_all([user, product])
        db.session.commit()
        product_id = product.id

    # Login
    client.post(
        "/api/auth/login",
        json={"email": "checkout@example.com", "password": "Pass123"},
    )

    # Add to cart
    client.post("/api/cart", json={"product_id": product_id, "quantity": 1})

    # Checkout
    response = client.post("/api/checkout")
    assert response.status_code == 200
    assert response.json["message"] == "Заказ оформлен"


def test_admin_access(client, app):
    """Test admin-only endpoints require admin role."""
    with app.app_context():
        from app import bcrypt

        admin = User(
            email="admin@test.com",
            password_hash=bcrypt.generate_password_hash("Admin123").decode("utf-8"),
            role="admin",
        )
        db.session.add(admin)
        db.session.commit()

    # Login as admin
    client.post(
        "/api/auth/login", json={"email": "admin@test.com", "password": "Admin123"}
    )

    # Access admin endpoint
    response = client.get("/api/admin/users")
    assert response.status_code == 200
    assert "users" in response.json
