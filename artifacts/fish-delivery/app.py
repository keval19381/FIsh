import os
import hashlib
import uuid
from functools import wraps
from datetime import datetime, timedelta
from supabase import create_client, Client
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
import razorpay
from flask_mail import Mail, Message
import random
import string
from dotenv import load_dotenv

# Load environment variables from the root project first, then fall back to artifact .env
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(project_root, '.env'))
load_dotenv()
if not os.getenv("SUPABASE_URL"):
    load_dotenv(dotenv_path=os.path.join(project_root, '.env'))

# Set paths explicitly so running from the artifacts folder doesn't break template/static routing
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
app = Flask(__name__, 
            template_folder=os.path.join(_project_root, 'templates'), 
            static_folder=os.path.join(_project_root, 'static'))
app.secret_key = os.environ.get("SESSION_SECRET", "aquabasket-secret-key-2024")

# Razorpay configuration
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_your_key_here")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "your_secret_here")
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Flask-Mail configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

# Debug email config
app.logger.debug(f"Mail config: SERVER={app.config.get('MAIL_SERVER')}, PORT={app.config.get('MAIL_PORT')}, TLS={app.config.get('MAIL_USE_TLS')}, USER={app.config.get('MAIL_USERNAME', 'NOT SET')}")

mail = Mail(app)

UPLOAD_FOLDER = os.path.join(_project_root, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# Supabase Initialization
import sys

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("ERROR: Supabase environment variables not loaded")
    exit(1)

# Ensure correct Supabase key usage
SUPABASE_ANON_KEY = SUPABASE_ANON_KEY.strip().strip("'").strip('"')
if not SUPABASE_ANON_KEY.startswith("eyJ"):
    print("ERROR: Invalid Supabase Anon Key. Must be a JWT starting with 'eyJ'. Rejecting key format.")
    exit(1)

# Debug logging
print(f"SUPABASE_URL: {SUPABASE_URL}")
print(f"SUPABASE_ANON_KEY: {SUPABASE_ANON_KEY[:10]}... (masked)")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
except Exception as e:
    print(f"ERROR: Supabase initialization failed: {e}")
    exit(1)

# ── Auto-Insert Demo Fish Data ─────────────────────────────────────────────
# This runs once at startup to ensure demo data exists for recording/demo purposes
def insert_demo_fish_if_empty():
    try:
        # Check if fish_items table is empty
        result = supabase.table("fish_items").select("id", count="exact").execute()
        
        if result.count == 0:
            # Table is empty, insert demo fish
            demo_fish = {
                "name": "Fresh Rohu Fish",
                "price": 299,
                "description": "Freshly caught Rohu fish, cleaned and ready to cook.",
                "image_url": "https://www.dreamstime.com/photos-images/rui-fish.html"
            }
            supabase.table("fish_items").insert(demo_fish).execute()
            print("✓ Demo fish added to database")
        else:
            print(f"Fish items table already contains {result.count} item(s). Skipping demo insert.")
    except Exception as e:
        print(f"! Warning: Could not insert demo fish data: {e}")

# Call demo insert on startup
insert_demo_fish_if_empty()

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    if isinstance(error, HTTPException):
        return error
    print("ERROR:", error)
    app.logger.exception("Unexpected error")
    flash("Something went wrong. Please try again.", "error")
    return redirect(url_for("index"))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def gen_otp():
    return ''.join(random.choices(string.digits, k=6))

def gen_order_number():
    import time
    timestamp = str(int(time.time()))
    random_part = ''.join(random.choices(string.digits, k=4))
    return f"ORD{timestamp}{random_part}"

def send_email(to, subject, template, **kwargs):
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        app.logger.error('Flask-Mail credentials are not configured. Set MAIL_USERNAME and MAIL_PASSWORD in .env.')
        return False

    sender = app.config.get('MAIL_DEFAULT_SENDER') or app.config.get('MAIL_USERNAME')
    app.logger.debug(f"Preparing email to {to} using sender {sender}")
    try:
        msg = Message(subject, recipients=[to], sender=sender)
        from jinja2.exceptions import TemplateNotFound
        try:
            msg.html = render_template(template, **kwargs)
        except TemplateNotFound as e:
            app.logger.error(f"FATAL: Email template '{template}' not found! Placed fallback. Error: {e}")
            msg.html = f"<html><body><h1>Verification</h1><p>Your OTP is: {kwargs.get('otp_code', 'MISSING')}</p></body></html>"
            
        mail.send(msg)
        app.logger.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as e:
        app.logger.exception(f"Email error sending to {to}: {e}")
        return False

def detect_new_device(user_id, current_ip, current_ua):
    response = supabase.table("users").select("login_ip, login_user_agent").eq("id", user_id).execute()
    user = response.data[0] if response.data else None
    
    if not user or not user.get('login_ip'):
        return False
    
    return user['login_ip'] != current_ip or user['login_user_agent'] != current_ua


# Supabase uses its own database for schema setup (see supabase_schema.sql)
def init_db():
    pass


# ── Decorators ─────────────────────────────────────────────────────────────


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login"))
            if session.get("user_role") not in roles:
                flash("You don't have permission to access this page.", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)

        return decorated

    return decorator


# ── Home ────────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    try:
        fish_res = supabase.table("fish").select("id", count="exact").eq("available", 1).execute()
        fish_count = fish_res.count if fish_res.count is not None else 0
        order_res = supabase.table("orders").select("id", count="exact").execute()
        order_count = order_res.count if order_res.count is not None else 0
        seller_res = supabase.table("users").select("id", count="exact").eq("role", "seller").execute()
        seller_count = seller_res.count if seller_res.count is not None else 0
    except Exception as e:
        app.logger.error(f"Supabase error on index: {e}")
        fish_count = order_count = seller_count = 0
    return render_template(
        "index.html",
        fish_count=fish_count,
        order_count=order_count,
        seller_count=seller_count,
    )


@app.route("/fish")
def fish_demo():
    """Display demo fish items for recording purposes."""
    try:
        result = supabase.table("fish_items").select("*").execute()
        fish_items = result.data if result.data else []
    except Exception as e:
        app.logger.error(f"Error fetching fish items: {e}")
        fish_items = []
    
    return render_template("fish.html", fish_items=fish_items)


# ── Auth ─────────────────────────────────────────────────────────────────────


@app.route("/auth/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("role_home"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        otp = request.form.get("otp", "").strip()
        
        if not email or not password:
            flash("Email and password are required.", "error")
        else:
            response = supabase.table("users").select("*").eq("email", email).eq("password_hash", hash_password(password)).execute()
            user = response.data[0] if response.data else None
            
            if user:
                # Check if email is verified
                if not user["email_verified"]:
                    # Generate and send OTP
                    otp_code = gen_otp()
                    otp_expires = datetime.now() + timedelta(minutes=10)
                    
                    supabase.table("users").update({
                        "otp_code": otp_code,
                        "otp_expires": otp_expires.isoformat()
                    }).eq("id", user["id"]).execute()
                    
                    sent = send_email(
                        user["email"], 
                        "Verify Your Email - AquaBasket", 
                        "emails/verify_email.html",
                        user_name=user["name"],
                        otp_code=otp_code
                    )
                    if not sent:
                        supabase.table("users").update({
                            "otp_code": None,
                            "otp_expires": None
                        }).eq("id", user["id"]).execute()
                        flash("Unable to send verification email. Please check SMTP settings and try again.", "error")
                        return render_template("auth/login.html")
                    
                    session["verify_user_id"] = user["id"]
                    app.logger.debug(f"Generated email verification OTP {otp_code} for user {user['email']}")
                    flash("Please check your email for verification code.", "info")
                    return redirect(url_for("verify_otp"))
                
                # Check OTP if provided
                if otp:
                    if user["otp_code"] == otp and datetime.now() < datetime.fromisoformat(user["otp_expires"]):
                        # Clear OTP
                        supabase.table("users").update({
                            "otp_code": None,
                            "otp_expires": None
                        }).eq("id", user["id"]).execute()
                        
                        # Update login info
                        current_ip = request.remote_addr
                        current_ua = request.headers.get('User-Agent', '')
                        
                        # Check for new device
                        is_new_device = detect_new_device(user["id"], current_ip, current_ua)
                        
                        supabase.table("users").update({
                            "last_login": datetime.now().isoformat(),
                            "login_ip": current_ip,
                            "login_user_agent": current_ua
                        }).eq("id", user["id"]).execute()
                        
                        session["user_id"] = user["id"]
                        session["user_name"] = user["name"]
                        session["user_role"] = user["role"]
                        session["user_email"] = user["email"]
                        
                        # Send login alert
                        send_email(
                            user["email"],
                            "New Login Detected - AquaBasket",
                            "emails/login_alert.html",
                            user_name=user["name"],
                            login_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            ip_address=current_ip,
                            user_agent=current_ua,
                            is_new_device=is_new_device
                        )
                        
                        flash(f"Welcome back, {user['name']}! 👋", "success")
                        return redirect(url_for("role_home"))
                    else:
                        flash("Invalid or expired OTP.", "error")
                else:
                    # Generate OTP for verified users too (2FA)
                    otp_code = gen_otp()
                    otp_expires = datetime.now() + timedelta(minutes=10)
                    
                    supabase.table("users").update({
                        "otp_code": otp_code,
                        "otp_expires": otp_expires.isoformat()
                    }).eq("id", user["id"]).execute()
                    
                    sent = send_email(
                        user["email"], 
                        "Login Verification - AquaBasket", 
                        "emails/login_otp.html",
                        user_name=user["name"],
                        otp_code=otp_code
                    )
                    if not sent:
                        supabase.table("users").update({
                            "otp_code": None,
                            "otp_expires": None
                        }).eq("id", user["id"]).execute()
                        flash("Unable to send login OTP. Please check SMTP settings and try again.", "error")
                        return render_template("auth/login.html")
                    
                    session["login_user_id"] = user["id"]
                    app.logger.debug(f"Generated login OTP {otp_code} for user {user['email']}")
                    flash("Please check your email for login verification code.", "info")
                    return redirect(url_for("login_otp"))
            else:
                flash("Invalid email or password.", "error")
    return render_template("auth/login.html")


@app.route("/auth/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("role_home"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "customer")
        city = request.form.get("city", "").strip()

        if not name or not email or not password:
            flash("Name, email and password are required.", "error")
        elif role not in ("seller", "customer", "delivery"):
            flash("Invalid role selected.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        else:
            try:
                # Generate OTP
                otp_code = gen_otp()
                otp_expires = datetime.now() + timedelta(minutes=10)
                
                response = supabase.table("users").insert({
                    "name": name,
                    "email": email,
                    "password_hash": hash_password(password),
                    "role": role,
                    "city": city,
                    "otp_code": otp_code,
                    "otp_expires": otp_expires.isoformat()
                }).execute()
                user_id = response.data[0]["id"]
                
                sent = send_email(
                    email,
                    "Verify Your Email - FishDelivery",
                    "emails/verify_email.html",
                    user_name=name,
                    otp_code=otp_code
                )
                if not sent:
                    supabase.table("users").update({
                        "otp_code": None,
                        "otp_expires": None
                    }).eq("id", user_id).execute()
                    print("ERROR: Registration welcome email failed to send, gracefully falling back")
                    flash("Registered successfully, but we could not send the verification email. Please check your SMTP settings or verify later.", "warning")
                    return redirect(url_for("login"))
                
                session["verify_user_id"] = user_id
                app.logger.debug(f"Generated signup OTP {otp_code} for new user {email}")
                flash("Please check your email for verification code.", "info")
                return redirect(url_for("verify_otp"))
            except Exception as e:
                print("ERROR:", e)
                flash(f"Error occurred during registration: {e}", "error")
    return render_template("auth/register.html")


@app.route("/auth/verify-otp", methods=["GET", "POST"])
def verify_otp():
    user_id = session.get("verify_user_id")
    if not user_id:
        flash("No verification in progress.", "error")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        
        response = supabase.table("users").select("*").eq("id", user_id).eq("otp_code", otp).gt("otp_expires", datetime.now().isoformat()).execute()
        user = response.data[0] if response.data else None
        
        if user:
            supabase.table("users").update({
                "email_verified": True,
                "otp_code": None,
                "otp_expires": None
            }).eq("id", user_id).execute()
            
            # Send welcome email
            send_email(
                user["email"],
                "Welcome to AquaBasket!",
                "emails/welcome.html",
                user_name=user["name"],
                signup_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            session.pop("verify_user_id", None)
            flash("Email verified successfully! You can now log in.", "success")
            return redirect(url_for("login"))
        else:
            flash("Invalid or expired OTP.", "error")
    
    return render_template("auth/verify_otp.html")


@app.route("/auth/login-otp", methods=["GET", "POST"])
def login_otp():
    user_id = session.get("login_user_id")
    if not user_id:
        flash("No login in progress.", "error")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        
        response = supabase.table("users").select("*").eq("id", user_id).eq("otp_code", otp).gt("otp_expires", datetime.now().isoformat()).execute()
        user = response.data[0] if response.data else None
        
        if user:
            # Clear OTP and update login info
            current_ip = request.remote_addr
            current_ua = request.headers.get('User-Agent', '')
            
            is_new_device = detect_new_device(user["id"], current_ip, current_ua)
            
            supabase.table("users").update({
                "otp_code": None,
                "otp_expires": None,
                "last_login": datetime.now().isoformat(),
                "login_ip": current_ip,
                "login_user_agent": current_ua
            }).eq("id", user["id"]).execute()
            
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]
            session["user_email"] = user["email"]
            
            # Send login alert
            send_email(
                user["email"],
                "New Login Detected - FishDelivery",
                "emails/login_alert.html",
                user_name=user["name"],
                login_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ip_address=current_ip,
                user_agent=current_ua,
                is_new_device=is_new_device
            )
            
            session.pop("login_user_id", None)
            flash(f"Welcome back, {user['name']}! 👋", "success")
            return redirect(url_for("role_home"))
        else:
            flash("Invalid or expired OTP.", "error")
    
    return render_template("auth/login_otp.html")


@app.route("/auth/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        
        response = supabase.table("users").select("*").eq("email", email).execute()
        user = response.data[0] if response.data else None
        
        if user:
            # Generate reset token
            reset_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
            reset_expires = datetime.now() + timedelta(hours=1)
            
            supabase.table("users").update({
                "reset_token": reset_token,
                "reset_expires": reset_expires.isoformat()
            }).eq("id", user["id"]).execute()
            
            # Send reset email
            reset_url = url_for('reset_password', token=reset_token, _external=True)
            send_email(
                email,
                "Password Reset - AquaBasket",
                "emails/password_reset.html",
                user_name=user["name"],
                reset_url=reset_url
            )
            
            flash("Password reset link sent to your email.", "info")
            return redirect(url_for("login"))
        else:
            flash("Email not found.", "error")
    
    return render_template("auth/forgot_password.html")


@app.route("/auth/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    response = supabase.table("users").select("*").eq("reset_token", token).gt("reset_expires", datetime.now().isoformat()).execute()
    user = response.data[0] if response.data else None
    
    if not user:
        flash("Invalid or expired reset link.", "error")
        return redirect(url_for("forgot_password"))
    
    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        if not password or len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            supabase.table("users").update({
                "password_hash": hash_password(password),
                "reset_token": None,
                "reset_expires": None
            }).eq("id", user["id"]).execute()
            
            flash("Password reset successfully! Please log in.", "success")
            return redirect(url_for("login"))
    
    return render_template("auth/reset_password.html")


@app.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


@app.route("/role-home")
@login_required
def role_home():
    role = session.get("user_role")
    if role == "seller":
        return redirect(url_for("seller_login_dashboard"))
    elif role == "customer":
        return redirect(url_for("customer_browse"))
    elif role == "admin":
        return redirect(url_for("delivery_login_dashboard"))
    elif role == "delivery":
        return redirect(url_for("delivery_login_dashboard"))
    return redirect(url_for("index"))


# ── Seller Login Dashboard ──────────────────────────────────────────────────


@app.route("/seller/login-dashboard")
@role_required("seller", "admin")
def seller_login_dashboard():
    """Welcome dashboard for sellers after login"""
    try:
        # Get seller's products
        fish_res = supabase.table("fish").select("*").eq("seller_id", session["user_id"]).execute()
        fish_list = fish_res.data if fish_res.data else []
        total_products = len(fish_list)
        in_stock = len([f for f in fish_list if f.get("available", 0) == 1])
        
        # Get seller's orders
        orders_res = supabase.table("orders").select("total_price, status, fish!inner(seller_id)").eq("fish.seller_id", session["user_id"]).execute()
        orders_data = orders_res.data if orders_res.data else []
        total_orders = len(orders_data)
        pending_orders = len([o for o in orders_data if o["status"] in ("pending", "preparing")])
        delivered_orders = len([o for o in orders_data if o["status"] == "delivered"])
        total_revenue = sum([o["total_price"] for o in orders_data if o["status"] == "delivered"])
        avg_rating = 4.8  # Default rating for demo
        
        return render_template(
            "seller/login_dashboard.html",
            total_products=total_products,
            in_stock=in_stock,
            total_orders=total_orders,
            pending_orders=pending_orders,
            delivered_orders=delivered_orders,
            total_revenue=total_revenue,
            avg_rating=avg_rating,
            session=session
        )
    except Exception as e:
        app.logger.error(f"Seller login dashboard error: {e}")
        return redirect(url_for("seller_dashboard"))


# ── Delivery Login Dashboard ────────────────────────────────────────────────


@app.route("/delivery/login-dashboard")
@role_required("delivery", "admin")
def delivery_login_dashboard():
    """Welcome dashboard for delivery agents after login"""
    try:
        # Get delivery agent's orders
        if session.get("user_role") == "delivery":
            orders_res = supabase.table("orders").select("*").eq("assigned_to", session["user_id"]).execute()
        else:
            # Admin sees all orders
            orders_res = supabase.table("orders").select("*").execute()
        
        orders_data = orders_res.data if orders_res.data else []
        total_assigned = len(orders_data)
        active_orders = len([o for o in orders_data if o["status"] in ("pending", "preparing", "out_for_delivery")])
        completed_orders = len([o for o in orders_data if o["status"] == "delivered"])
        
        # Get pending unassigned orders
        unassigned_res = supabase.table("orders").select("*", count="exact").is_("assigned_to", "null").execute()
        pending_assignments = unassigned_res.count if unassigned_res.count is not None else 0
        
        return render_template(
            "delivery/login_dashboard.html",
            total_assigned=total_assigned,
            active_orders=active_orders,
            completed_orders=completed_orders,
            pending_assignments=pending_assignments,
            session=session
        )
    except Exception as e:
        app.logger.error(f"Delivery login dashboard error: {e}")
        return redirect(url_for("delivery_orders"))


# ── Seller ───────────────────────────────────────────────────────────────────


@app.route("/seller")
@role_required("seller", "admin")
def seller_dashboard():
    if session["user_role"] == "seller":
        fish_res = supabase.table("fish").select("*").eq("seller_id", session["user_id"]).order("id", desc=True).execute()
        fish_list = fish_res.data if fish_res.data else []
    else:
        fish_res = supabase.table("fish").select("*, users!inner(name)").order("id", desc=True).execute()
        fish_list = []
        if fish_res.data:
            for f in fish_res.data:
                f["seller_name"] = f["users"]["name"] if f.get("users") else ""
                fish_list.append(f)

    orders_res = supabase.table("orders").select("total_price, status, fish!inner(seller_id)").eq("fish.seller_id", session["user_id"]).execute()
    total_orders = len(orders_res.data) if orders_res.data else 0
    revenue = sum(o["total_price"] for o in orders_res.data if o["status"] == "delivered") if orders_res.data else 0
    return render_template(
        "seller/dashboard.html",
        fish_list=fish_list,
        total_orders=total_orders,
        revenue=revenue,
    )


@app.route("/seller/add", methods=["GET", "POST"])
@role_required("seller", "admin")
def seller_add_fish():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price", "").strip()
        description = request.form.get("description", "").strip()
        image_path = ""

        if not name or not price:
            flash("Fish name and price are required.", "error")
            return render_template("seller/add_fish.html")

        try:
            price_val = float(price)
            if price_val <= 0:
                raise ValueError
        except ValueError:
            flash("Price must be a positive number.", "error")
            return render_template("seller/add_fish.html")

        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                image_path = f"uploads/{filename}"

        supabase.table("fish").insert({
            "seller_id": session["user_id"],
            "name": name,
            "price": price_val,
            "image_path": image_path,
            "description": description
        }).execute()
        flash(f'"{name}" added successfully! 🐟', "success")
        return redirect(url_for("seller_dashboard"))

    return render_template("seller/add_fish.html")


@app.route("/seller/fish/toggle/<int:fish_id>", methods=["POST"])
@role_required("seller", "admin")
def seller_toggle(fish_id):
    res = supabase.table("fish").select("*").eq("id", fish_id).execute()
    fish = res.data[0] if res.data else None
    if fish:
        supabase.table("fish").update({
            "available": 0 if fish["available"] else 1
        }).eq("id", fish_id).execute()
    flash("Availability updated.", "success")
    return redirect(url_for("seller_dashboard"))


@app.route("/seller/fish/delete/<int:fish_id>", methods=["POST"])
@role_required("seller", "admin")
def seller_delete(fish_id):
    res = supabase.table("fish").select("*").eq("id", fish_id).execute()
    fish = res.data[0] if res.data else None
    if fish and fish.get("image_path"):
        img = os.path.join(os.path.dirname(__file__), "static", fish["image_path"])
        if os.path.exists(img):
            os.remove(img)
    supabase.table("fish").delete().eq("id", fish_id).execute()
    flash("Fish removed.", "success")
    return redirect(url_for("seller_dashboard"))


# ── Customer ─────────────────────────────────────────────────────────────────


@app.route("/customer")
@role_required("customer", "admin")
def customer_browse():
    query = request.args.get("q", "").strip()
    if query:
        fish_res = supabase.table("fish").select("*").eq("available", 1).ilike("name", f"%{query}%").order("name").execute()
    else:
        fish_res = supabase.table("fish").select("*").eq("available", 1).order("name").execute()
    fish_list = fish_res.data if fish_res.data else []
    return render_template("customer/browse.html", fish_list=fish_list, query=query)


@app.route("/customer/order/<int:fish_id>", methods=["GET", "POST"])
@role_required("customer", "admin")
def customer_order(fish_id):
    res = supabase.table("fish").select("*").eq("id", fish_id).eq("available", 1).execute()
    fish = res.data[0] if res.data else None
    if not fish:
        flash("This fish is no longer available.", "error")
        return redirect(url_for("customer_browse"))

    if request.method == "POST":
        qty_str = request.form.get("quantity", "1").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()

        try:
            qty = float(qty_str)
            if qty <= 0:
                raise ValueError
        except ValueError:
            flash("Quantity must be a positive number.", "error")
            return render_template("customer/order.html", fish=fish)

        if not address:
            flash("Delivery address is required.", "error")
            return render_template("customer/order.html", fish=fish)

        total = round(fish["price"] * qty, 2)
        order_num = gen_order_number()
        order_res = supabase.table("orders").insert({
            "order_number": order_num,
            "customer_id": session["user_id"],
            "fish_id": fish_id,
            "quantity": qty,
            "total_price": total,
            "delivery_address": address,
            "delivery_city": city
        }).execute()
        order_id = order_res.data[0]["id"]
        flash(f"Order placed successfully! Order ID: {order_num}", "success")
        return redirect(url_for("customer_confirm", order_id=order_id))

    return render_template("customer/order.html", fish=fish)


@app.route("/customer/confirm/<int:order_id>")
@role_required("customer", "admin")
def customer_confirm(order_id):
    order_res = supabase.table("orders").select("*, fish!inner(name, price, image_path)").eq("id", order_id).eq("customer_id", session["user_id"]).execute()
    raw_order = order_res.data[0] if order_res.data else None
    if not raw_order:
        return redirect(url_for("customer_browse"))
        
    order = dict(raw_order)
    order["fish_name"] = raw_order["fish"]["name"]
    order["fish_price"] = raw_order["fish"]["price"]
    order["image_path"] = raw_order["fish"]["image_path"]
    return render_template("customer/confirm.html", order=order)


@app.route("/customer/orders")
@role_required("customer", "admin")
def customer_orders():
    orders_res = supabase.table("orders").select("*, fish!inner(name, image_path), users!assigned_to(name)").eq("customer_id", session["user_id"]).order("created_at", desc=True).execute()
    orders = []
    if orders_res.data:
        for o in orders_res.data:
            order_dict = dict(o)
            order_dict["fish_name"] = o["fish"]["name"] if o.get("fish") else ""
            order_dict["image_path"] = o["fish"]["image_path"] if o.get("fish") else ""
            order_dict["partner_name"] = o["users"]["name"] if o.get("users") else ""
            orders.append(order_dict)
    return render_template("customer/orders.html", orders=orders)


# ── Cart ────────────────────────────────────────────────────────────────────


@app.route("/cart")
@role_required("customer", "admin")
def cart():
    cart_items = session.get("cart", {})
    items = []
    total = 0
    if cart_items:
        for fish_id, qty in cart_items.items():
            res = supabase.table("fish").select("*").eq("id", int(fish_id)).eq("available", 1).execute()
            fish = res.data[0] if res.data else None
            if fish:
                subtotal = fish["price"] * qty
                total += subtotal
                items.append({
                    "id": fish["id"],
                    "name": fish["name"],
                    "price": fish["price"],
                    "quantity": qty,
                    "subtotal": subtotal,
                    "image_path": fish["image_path"]
                })
    return render_template("customer/cart.html", items=items, total=total)


@app.route("/cart/add/<int:fish_id>", methods=["POST"])
@role_required("customer", "admin")
def add_to_cart(fish_id):
    res = supabase.table("fish").select("*").eq("id", fish_id).eq("available", 1).execute()
    fish = res.data[0] if res.data else None
    if not fish:
        flash("Fish not available.", "error")
        return redirect(url_for("customer_browse"))
    
    cart = session.get("cart", {})
    cart[str(fish_id)] = cart.get(str(fish_id), 0) + 1
    session["cart"] = cart
    flash(f"{fish['name']} added to cart!", "success")
    return redirect(request.referrer or url_for("customer_browse"))


@app.route("/cart/update/<int:fish_id>", methods=["POST"])
@role_required("customer", "admin")
def update_cart(fish_id):
    qty = int(request.form.get("quantity", 1))
    cart = session.get("cart", {})
    if qty <= 0:
        cart.pop(str(fish_id), None)
    else:
        cart[str(fish_id)] = qty
    session["cart"] = cart
    return redirect(url_for("cart"))


@app.route("/cart/count")
@role_required("customer", "admin")
def cart_count():
    cart = session.get("cart", {})
    count = sum(cart.values())
    return jsonify({"count": count})


@app.route("/cart/checkout", methods=["GET", "POST"])
@role_required("customer", "admin")
def checkout():
    cart_items = session.get("cart", {})
    if not cart_items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("cart"))
    
    # Calculate total
    items = []
    total = 0
    for fish_id, qty in cart_items.items():
        res = supabase.table("fish").select("*").eq("id", int(fish_id)).eq("available", 1).execute()
        fish = res.data[0] if res.data else None
        if fish:
            subtotal = fish["price"] * qty
            total += subtotal
            items.append({
                "name": fish["name"],
                "quantity": qty,
                "subtotal": subtotal
            })
    
    if request.method == "POST":
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        if not address or not city:
            flash("Delivery address and city are required.", "error")
            return redirect(url_for("checkout"))
        
        # Create Razorpay order
        amount_in_paise = int(total * 100)  # Convert to paise
        razorpay_order = razorpay_client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "payment_capture": "1"
        })
        
        # Store order details in session for payment verification
        session["pending_order"] = {
            "cart": cart_items,
            "address": address,
            "city": city,
            "total": total,
            "razorpay_order_id": razorpay_order["id"]
        }
        
        return render_template("customer/payment.html", 
                             order=razorpay_order, 
                             items=items, 
                             total=total,
                             key_id=RAZORPAY_KEY_ID)
    
    # GET request: show checkout form
    return render_template("customer/checkout.html", items=items, total=total)


@app.route("/payment/verify", methods=["POST"])
@role_required("customer", "admin")
def verify_payment():
    data = request.get_json()
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")
    
    # Verify payment signature
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    
    try:
        razorpay_client.utility.verify_payment_signature(params_dict)
        
        # Payment verified, create orders
        pending_order = session.get("pending_order")
        if not pending_order:
            return jsonify({"success": False, "message": "No pending order found"})
        
        total_orders = 0
        for fish_id, qty in pending_order["cart"].items():
            res = supabase.table("fish").select("*").eq("id", int(fish_id)).eq("available", 1).execute()
            fish = res.data[0] if res.data else None
            if fish:
                total_price = fish["price"] * qty
                order_number = gen_order_number()
                supabase.table("orders").insert({
                    "order_number": order_number,
                    "customer_id": session["user_id"],
                    "fish_id": int(fish_id),
                    "quantity": qty,
                    "total_price": total_price,
                    "delivery_address": pending_order["address"],
                    "delivery_city": pending_order["city"]
                }).execute()
                total_orders += 1
        
        if total_orders > 0:
            session.pop("cart", None)
            session.pop("pending_order", None)
            return jsonify({"success": True, "message": f"Order placed successfully! {total_orders} item(s) ordered."})
        else:
            return jsonify({"success": False, "message": "No valid items in cart"})
            
    except Exception as e:
        return jsonify({"success": False, "message": "Payment verification failed"})


# ── Delivery ─────────────────────────────────────────────────────────────────


@app.route("/delivery")
@login_required
def delivery_home():
    role = session.get("user_role")
    if role == "admin":
        return redirect(url_for("delivery_admin"))
    elif role == "delivery":
        return redirect(url_for("delivery_orders"))
    flash("Delivery partner or admin access required.", "error")
    return redirect(url_for("index"))


@app.route("/delivery/orders")
@role_required("delivery", "admin")
def delivery_orders():
    status_filter = request.args.get("status", "all")
    base_q = supabase.table("orders").select("*, fish!inner(name, price), users!customer_id(name, city)").eq("assigned_to", session["user_id"])
    if status_filter != "all":
        orders_res = base_q.eq("status", status_filter).order("created_at", desc=True).execute()
    else:
        orders_res = base_q.order("created_at", desc=True).execute()
    
    orders = []
    if orders_res.data:
        for o in orders_res.data:
            order_dict = dict(o)
            order_dict["fish_name"] = o["fish"]["name"] if o.get("fish") else ""
            order_dict["fish_price"] = o["fish"]["price"] if o.get("fish") else ""
            order_dict["customer_name"] = o["users"]["name"] if o.get("users") else ""
            order_dict["customer_city"] = o["users"]["city"] if o.get("users") else ""
            orders.append(order_dict)
    return render_template(
        "delivery/my_orders.html", orders=orders, status_filter=status_filter
    )


@app.route("/delivery/orders/update/<int:order_id>", methods=["POST"])
@role_required("delivery", "admin")
def delivery_update(order_id):
    new_status = request.form.get("status")
    valid = ["pending", "preparing", "out_for_delivery", "delivered", "cancelled"]
    if new_status in valid:
        supabase.table("orders").update({"status": new_status}).eq("id", order_id).eq("assigned_to", session["user_id"]).execute()
        flash("Order status updated.", "success")
    return redirect(url_for("delivery_orders"))


@app.route("/delivery/admin")
@role_required("admin")
def delivery_admin():
    status_filter = request.args.get("status", "all")
    base_q = supabase.table("orders").select("*, fish!inner(name, price), customer:users!customer_id(name), partner:users!assigned_to(name)")
    if status_filter != "all":
        orders_res = base_q.eq("status", status_filter).order("created_at", desc=True).execute()
    else:
        orders_res = base_q.order("created_at", desc=True).execute()
    
    orders = []
    if orders_res.data:
        for o in orders_res.data:
            order_dict = dict(o)
            order_dict["fish_name"] = o["fish"]["name"] if o.get("fish") else ""
            order_dict["fish_price"] = o["fish"]["price"] if o.get("fish") else ""
            order_dict["customer_name"] = o.get("customer", {}).get("name") if o.get("customer") else ""
            order_dict["partner_name"] = o.get("partner", {}).get("name") if o.get("partner") else ""
            orders.append(order_dict)

    partners_res = supabase.table("users").select("id, name, city").in_("role", ["delivery", "admin"]).order("name").execute()
    partners = partners_res.data if partners_res.data else []

    all_orders = supabase.table("orders").select("status, total_price, assigned_to").execute().data or []
    stats = {
        "total": len(all_orders),
        "pending": len([o for o in all_orders if o["status"] == "pending"]),
        "active": len([o for o in all_orders if o["status"] in ("preparing", "out_for_delivery")]),
        "delivered": len([o for o in all_orders if o["status"] == "delivered"]),
        "unassigned": len([o for o in all_orders if o.get("assigned_to") is None]),
        "revenue": sum([o["total_price"] for o in all_orders if o["status"] == "delivered"])
    }
    return render_template(
        "delivery/admin.html",
        orders=orders,
        partners=partners,
        stats=stats,
        status_filter=status_filter,
    )


@app.route("/delivery/admin/assign/<int:order_id>", methods=["POST"])
@role_required("admin")
def delivery_assign(order_id):
    partner_id = request.form.get("partner_id", "").strip()
    if partner_id:
        supabase.table("orders").update({"assigned_to": int(partner_id)}).eq("id", order_id).execute()
        p = supabase.table("users").select("name").eq("id", partner_id).execute()
        flash(f"Assigned to {p.data[0]['name'] if p.data else 'partner'}.", "success")
    else:
        supabase.table("orders").update({"assigned_to": None}).eq("id", order_id).execute()
        flash("Order unassigned.", "success")
    return redirect(url_for("delivery_admin"))


@app.route("/delivery/admin/status/<int:order_id>", methods=["POST"])
@role_required("admin")
def delivery_admin_status(order_id):
    new_status = request.form.get("status")
    valid = ["pending", "preparing", "out_for_delivery", "delivered", "cancelled"]
    if new_status in valid:
        supabase.table("orders").update({"status": new_status}).eq("id", order_id).execute()
        flash("Status updated.", "success")
    return redirect(url_for("delivery_admin"))


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
