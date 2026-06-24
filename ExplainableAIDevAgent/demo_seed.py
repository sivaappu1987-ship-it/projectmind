from datetime import datetime, timedelta, timezone

from backend.database.database import Base, SessionLocal, engine
from backend.models.commit import Commit
from backend.models.contributor import Contributor
from backend.models.documentation import Documentation
from backend.models.file import File
from backend.models.issue import Issue
from backend.models.merge_request import MergeRequest
from backend.models.project import Project


def run_demo_seed():
    print("Initializing ProjectMind AI demo database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        project = Project(
            id=1,
            gitlab_id=1001,
            name="AcmeCommerce Platform",
            description="Full-stack e-commerce platform with auth, checkout, payments, notifications, and user management.",
            visibility="private",
            created_at=now,
        )
        db.add(project)
        db.commit()

        # --- Contributors ---
        alice   = Contributor(id=1,  name="Alice Chen",    email="alice@acme.dev",   total_commits=312)
        bob     = Contributor(id=2,  name="Bob Martinez",  email="bob@acme.dev",     total_commits=187)
        maya    = Contributor(id=3,  name="Maya Patel",    email="maya@acme.dev",    total_commits=94)
        sam     = Contributor(id=4,  name="Sam Okafor",    email="sam@acme.dev",     total_commits=231)
        lee     = Contributor(id=5,  name="Lee Nguyen",    email="lee@acme.dev",     total_commits=156)
        priya   = Contributor(id=6,  name="Priya Singh",   email="priya@acme.dev",   total_commits=78)
        carlos  = Contributor(id=7,  name="Carlos Ruiz",   email="carlos@acme.dev",  total_commits=43)
        nina    = Contributor(id=8,  name="Nina Volkov",   email="nina@acme.dev",    total_commits=129)
        db.add_all([alice, bob, maya, sam, lee, priya, carlos, nina])
        db.commit()

        # --- Source Files ---
        auth_file = File(id=1, project_id=1, path="backend/auth.py", updated_at=now, content="""from datetime import datetime, timedelta
import jwt

SECRET_KEY = "super-secret-key"
TOKEN_TIMEOUT_MINUTES = 45
REFRESH_TOKEN_DAYS = 7

def create_access_token(user_id: int) -> str:
    expires_at = datetime.utcnow() + timedelta(minutes=TOKEN_TIMEOUT_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expires_at, "type": "access"}, SECRET_KEY, algorithm="HS256")

def create_refresh_token(user_id: int) -> str:
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_DAYS)
    return jwt.encode({"sub": user_id, "exp": expires_at, "type": "refresh"}, SECRET_KEY, algorithm="HS256")

def verify_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

def revoke_token(token: str, blacklist: set) -> None:
    blacklist.add(token)
""")

        login_file = File(id=2, project_id=1, path="backend/login.py", content="""from backend.auth import create_access_token, create_refresh_token
from backend.models.user import User

def login_user(email: str, password: str, db) -> dict:
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.check_password(password):
        raise ValueError("Invalid credentials")
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer"
    }
""")

        user_service = File(id=3, project_id=1, path="backend/user_service.py", content="""from typing import List
from backend.models.user import User

PERMISSION_MAP = {
    "admin":    ["orders:read", "orders:write", "profile:write", "users:manage", "payments:read"],
    "customer": ["orders:read", "profile:write"],
    "vendor":   ["orders:read", "orders:write", "products:manage"],
}

def get_user_permissions(user_id: int, db) -> List[str]:
    user = db.query(User).filter(User.id == user_id).first()
    return PERMISSION_MAP.get(user.role, []) if user else []

def update_user_profile(user_id: int, data: dict, db) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    return user
""")

        checkout = File(id=4, project_id=1, path="backend/checkout.py", content="""from backend.payments import charge_card
from backend.models.order import Order

def create_order(cart, user, db) -> dict:
    if not cart.items:
        raise ValueError("Cart is empty")
    total = sum(item.price * item.qty for item in cart.items)
    payment = charge_card(user.payment_method, total)
    order = Order(user_id=user.id, total=total, payment_id=payment.id, status="confirmed")
    db.add(order)
    db.commit()
    return {"status": "confirmed", "order_id": order.id, "total": total}

def cancel_order(order_id: int, db) -> dict:
    order = db.query(Order).filter(Order.id == order_id).first()
    if order.status == "shipped":
        raise ValueError("Cannot cancel a shipped order")
    order.status = "cancelled"
    db.commit()
    return {"status": "cancelled", "order_id": order_id}
""")

        payments = File(id=5, project_id=1, path="backend/payments.py", content="""import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def charge_card(payment_method_id: str, amount: float) -> dict:
    intent = stripe.PaymentIntent.create(
        amount=int(amount * 100),
        currency="usd",
        payment_method=payment_method_id,
        confirm=True,
    )
    return intent

def refund_payment(payment_intent_id: str, amount: float = None) -> dict:
    params = {"payment_intent": payment_intent_id}
    if amount:
        params["amount"] = int(amount * 100)
    return stripe.Refund.create(**params)
""")

        notifications = File(id=6, project_id=1, path="backend/notifications.py", content="""import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.acme.dev"

def send_email(to: str, subject: str, body: str) -> bool:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "noreply@acme.dev"
    msg["To"] = to
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_HOST, 587) as smtp:
            smtp.starttls()
            smtp.send_message(msg)
        return True
    except Exception:
        return False

def send_order_confirmation(user_email: str, order_id: int) -> bool:
    return send_email(user_email, f"Order #{order_id} Confirmed", f"Your order #{order_id} is confirmed!")

def send_password_reset(user_email: str, reset_link: str) -> bool:
    return send_email(user_email, "Reset your password", f"Click here to reset: {reset_link}")
""")

        products = File(id=7, project_id=1, path="backend/products.py", content="""from backend.models.product import Product

def get_product(product_id: int, db) -> Product:
    return db.query(Product).filter(Product.id == product_id).first()

def search_products(query: str, db, limit: int = 20) -> list:
    return db.query(Product).filter(Product.name.ilike(f"%{query}%")).limit(limit).all()

def update_inventory(product_id: int, delta: int, db) -> None:
    product = get_product(product_id, db)
    product.stock += delta
    if product.stock < 0:
        raise ValueError("Insufficient stock")
    db.commit()
""")

        cart_service = File(id=8, project_id=1, path="backend/cart_service.py", content="""from backend.models.cart import Cart, CartItem
from backend.products import get_product

def add_to_cart(user_id: int, product_id: int, qty: int, db) -> Cart:
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
    product = get_product(product_id, db)
    item = CartItem(cart=cart, product_id=product_id, price=product.price, qty=qty)
    db.add(item)
    db.commit()
    return cart

def clear_cart(user_id: int, db) -> None:
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if cart:
        for item in cart.items:
            db.delete(item)
        db.commit()
""")

        search_service = File(id=9, project_id=1, path="backend/search_service.py", content="""from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")
INDEX = "acme_products"

def index_product(product: dict) -> None:
    es.index(index=INDEX, id=product["id"], body=product)

def search(query: str, filters: dict = None) -> list:
    body = {"query": {"multi_match": {"query": query, "fields": ["name", "description", "tags"]}}}
    if filters:
        body["query"] = {"bool": {"must": body["query"], "filter": [{"term": {k: v}} for k, v in filters.items()]}}
    return es.search(index=INDEX, body=body)["hits"]["hits"]
""")

        admin_panel = File(id=10, project_id=1, path="frontend/admin_panel.py", content="""from fastapi import APIRouter, Depends
from backend.auth import verify_access_token
from backend.user_service import get_user_permissions

router = APIRouter(prefix="/admin", tags=["Admin"])

def require_admin(token: str = Depends(verify_access_token)):
    claims = verify_access_token(token)
    perms = get_user_permissions(claims["sub"], db=None)
    if "users:manage" not in perms:
        raise PermissionError("Admin access required")

@router.get("/users")
async def list_users():
    pass

@router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    pass
""")

        readme = File(id=11, project_id=1, path="README.md", content="""# AcmeCommerce Platform

Full-stack e-commerce platform powering auth, checkout, payments, product management, cart, notifications, and admin tools.

## Modules
- `auth.py` - JWT access + refresh tokens
- `login.py` - User login flow
- `checkout.py` - Order creation and cancellation
- `payments.py` - Stripe integration
- `notifications.py` - Email notifications
- `products.py` - Product catalogue and inventory
- `cart_service.py` - Shopping cart management
- `search_service.py` - Elasticsearch product search
- `user_service.py` - Permissions and profiles

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env
python demo_seed.py
```
""")

        db.add_all([auth_file, login_file, user_service, checkout, payments,
                    notifications, products, cart_service, search_service, admin_panel, readme])
        db.commit()

        # --- Documentation ---
        auth_doc = Documentation(id=1, title="authentication.md",
            content="JWT tokens expire after 45 minutes. Refresh tokens are valid for 7 days. Use POST /auth/refresh to rotate. Tokens can be revoked via the blacklist mechanism.",
            file_id=auth_file.id, updated_at=now - timedelta(days=12))
        payments_doc = Documentation(id=2, title="payments-integration.md",
            content="Stripe is used for payment processing. Set STRIPE_SECRET_KEY in .env. Use charge_card() for purchases. refund_payment() handles full and partial refunds.",
            file_id=payments.id, updated_at=now - timedelta(days=3))
        onboarding_doc = Documentation(id=3, title="developer-onboarding.md",
            content="Start with README.md. Read authentication.md and payments-integration.md. Then pick a good first issue labelled 'beginner'. Mentor is assigned on first PR.",
            file_id=readme.id)
        checkout_doc = Documentation(id=4, title="checkout-flow.md",
            content="Checkout validates cart, charges via Stripe, creates an Order record, and sends a confirmation email. Cancel is only allowed before shipping.",
            file_id=checkout.id, updated_at=now - timedelta(days=7))
        notifications_doc = Documentation(id=5, title="notifications.md",
            content="Email is sent via SMTP. Order confirmations and password reset emails are currently supported. Extend send_email() for new templates.",
            file_id=notifications.id)
        db.add_all([auth_doc, payments_doc, onboarding_doc, checkout_doc, notifications_doc])

        # --- Issues ---
        issues = [
            Issue(id=1,  project_id=1, gitlab_issue_id=24,  title="Authentication timeout too short",
                  description="Users are logged out earlier than expected after auth token timeout changed from 60 to 45 min.",
                  state="opened", labels="bug, authentication, backend", assignee_id=alice.id),
            Issue(id=2,  project_id=1, gitlab_issue_id=31,  title="Login endpoint returns unclear 401 error",
                  description="Improve the error message when token validation fails to distinguish expired vs invalid tokens.",
                  state="opened", labels="authentication, good first issue, ux"),
            Issue(id=3,  project_id=1, gitlab_issue_id=45,  title="Update onboarding checklist link",
                  description="The onboarding README still points to the old authentication doc path.",
                  state="opened", labels="documentation, beginner, good first issue"),
            Issue(id=4,  project_id=1, gitlab_issue_id=52,  title="Checkout empty-cart validation missing",
                  description="Checkout should return a friendly 400 error when a cart is empty rather than crashing.",
                  state="opened", labels="backend, beginner, checkout"),
            Issue(id=5,  project_id=1, gitlab_issue_id=61,  title="Stripe webhook signature not verified",
                  description="Payment webhooks from Stripe are accepted without signature verification. Security risk.",
                  state="opened", labels="security, payments, critical", assignee_id=sam.id),
            Issue(id=6,  project_id=1, gitlab_issue_id=67,  title="Add product search filters by price range",
                  description="Search currently only supports text matching. Add min_price and max_price filter params.",
                  state="opened", labels="feature, search, backend"),
            Issue(id=7,  project_id=1, gitlab_issue_id=73,  title="Cart quantity update not persisted",
                  description="Updating qty in cart UI doesn't save to backend. Race condition suspected.",
                  state="opened", labels="bug, cart, frontend", assignee_id=lee.id),
            Issue(id=8,  project_id=1, gitlab_issue_id=78,  title="Email notifications fail silently on SMTP error",
                  description="send_email returns False on failure but callers don't check the return value.",
                  state="opened", labels="bug, notifications, reliability"),
            Issue(id=9,  project_id=1, gitlab_issue_id=82,  title="Admin panel missing pagination",
                  description="GET /admin/users returns all users with no limit. Will break at scale.",
                  state="opened", labels="backend, admin, performance"),
            Issue(id=10, project_id=1, gitlab_issue_id=88,  title="Write unit tests for auth.py",
                  description="No tests exist for create_access_token and verify_access_token.",
                  state="opened", labels="testing, authentication, good first issue"),
            Issue(id=11, project_id=1, gitlab_issue_id=33,  title="Migrate from HS256 to RS256 for JWT",
                  description="Use asymmetric keys so services can verify tokens without sharing the secret.",
                  state="closed", labels="security, authentication", assignee_id=alice.id),
            Issue(id=12, project_id=1, gitlab_issue_id=40,  title="Add Stripe refund support",
                  description="Implement partial and full refund via Stripe API.",
                  state="closed", labels="payments, feature", assignee_id=sam.id),
        ]
        db.add_all(issues)

        # --- Merge Requests ---
        db.add_all([
            MergeRequest(id=1,  project_id=1, gitlab_mr_id=10, title="Add JWT access + refresh tokens",
                         description="Introduces auth.py token creation, validation, and revocation.", state="merged", author_id=alice.id),
            MergeRequest(id=2,  project_id=1, gitlab_mr_id=11, title="Refactor user permissions lookup",
                         description="Adds PERMISSION_MAP and role-based access control.", state="merged", author_id=bob.id),
            MergeRequest(id=3,  project_id=1, gitlab_mr_id=12, title="Stripe payment integration",
                         description="Adds charge_card and refund_payment using Stripe SDK.", state="merged", author_id=sam.id),
            MergeRequest(id=4,  project_id=1, gitlab_mr_id=13, title="Checkout flow with order model",
                         description="Wires cart -> payment -> order creation.", state="merged", author_id=lee.id),
            MergeRequest(id=5,  project_id=1, gitlab_mr_id=14, title="Email notification service",
                         description="SMTP email for order confirmation and password reset.", state="merged", author_id=nina.id),
            MergeRequest(id=6,  project_id=1, gitlab_mr_id=15, title="Elasticsearch product search",
                         description="Adds indexing and multi-field search with filters.", state="open", author_id=priya.id),
            MergeRequest(id=7,  project_id=1, gitlab_mr_id=16, title="Admin panel CRUD endpoints",
                         description="User list and delete with admin permission guard.", state="open", author_id=carlos.id),
        ])

        # --- Commits ---
        commits = [
            Commit(id=1,  project_id=1, contributor_id=alice.id,  hash="a100", message="Add backend/auth.py JWT create_access_token and verify_access_token"),
            Commit(id=2,  project_id=1, contributor_id=alice.id,  hash="a101", message="Fix authentication timeout handling in backend/auth.py"),
            Commit(id=3,  project_id=1, contributor_id=alice.id,  hash="a102", message="Add refresh token support and revocation blacklist to auth.py"),
            Commit(id=4,  project_id=1, contributor_id=alice.id,  hash="a103", message="Migrate JWT algorithm to HS256 with secret rotation support"),
            Commit(id=5,  project_id=1, contributor_id=bob.id,    hash="b200", message="Refactor backend/user_service.py permission lookup with PERMISSION_MAP"),
            Commit(id=6,  project_id=1, contributor_id=bob.id,    hash="b201", message="Add backend/checkout.py order validation and cart empty check"),
            Commit(id=7,  project_id=1, contributor_id=bob.id,    hash="b202", message="Fix checkout cancel_order to block cancellation after shipping"),
            Commit(id=8,  project_id=1, contributor_id=sam.id,    hash="s300", message="Integrate Stripe charge_card into backend/payments.py"),
            Commit(id=9,  project_id=1, contributor_id=sam.id,    hash="s301", message="Add refund_payment to backend/payments.py for partial and full refunds"),
            Commit(id=10, project_id=1, contributor_id=sam.id,    hash="s302", message="Fix Stripe payment intent confirmation in payments.py"),
            Commit(id=11, project_id=1, contributor_id=sam.id,    hash="s303", message="Add webhook endpoint stub for Stripe payment events"),
            Commit(id=12, project_id=1, contributor_id=lee.id,    hash="l400", message="Add backend/cart_service.py add_to_cart and clear_cart"),
            Commit(id=13, project_id=1, contributor_id=lee.id,    hash="l401", message="Fix cart_service qty update persistence bug"),
            Commit(id=14, project_id=1, contributor_id=lee.id,    hash="l402", message="Wire checkout.py to cart_service for order creation flow"),
            Commit(id=15, project_id=1, contributor_id=maya.id,   hash="m300", message="Update README.md onboarding checklist and module documentation"),
            Commit(id=16, project_id=1, contributor_id=maya.id,   hash="m301", message="Add developer-onboarding.md with setup and good first issue guide"),
            Commit(id=17, project_id=1, contributor_id=nina.id,   hash="n500", message="Add backend/notifications.py send_email and order confirmation"),
            Commit(id=18, project_id=1, contributor_id=nina.id,   hash="n501", message="Add password reset email to notifications.py"),
            Commit(id=19, project_id=1, contributor_id=priya.id,  hash="p600", message="Add backend/search_service.py Elasticsearch product indexing"),
            Commit(id=20, project_id=1, contributor_id=priya.id,  hash="p601", message="Add multi-field search with price filter support to search_service"),
            Commit(id=21, project_id=1, contributor_id=carlos.id, hash="c700", message="Add frontend/admin_panel.py user list and delete endpoints"),
            Commit(id=22, project_id=1, contributor_id=bob.id,    hash="b203", message="Add backend/products.py inventory update and search helpers"),
            Commit(id=23, project_id=1, contributor_id=alice.id,  hash="a104", message="Add login.py user login flow with access and refresh token return"),
            Commit(id=24, project_id=1, contributor_id=sam.id,    hash="s304", message="Update payments.py to handle Stripe declined card errors gracefully"),
            Commit(id=25, project_id=1, contributor_id=lee.id,    hash="l403", message="Refactor checkout to use cart_service.clear_cart after order creation"),
        ]
        db.add_all(commits)
        db.commit()
        print("ProjectMind AI demo database is ready.")
    finally:
        db.close()


if __name__ == "__main__":
    run_demo_seed()
