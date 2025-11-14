"""Routes that render HTML pages using the same Flask app."""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from .utils import role_required

pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/")
def landing():
    if current_user.is_authenticated:
        return render_template("dashboard.html")
    return render_template("index.html")


@pages_bp.get("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@pages_bp.get("/shop")
@login_required
def shop():
    return render_template("shop.html")


@pages_bp.get("/admin")
@role_required("admin")
def admin_panel():
    return render_template("admin.html")
