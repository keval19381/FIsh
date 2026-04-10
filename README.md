# AquaBasket - Professional Seafood Ordering Platform

A modern, secure seafood ordering platform built with Flask, featuring professional UI/UX, cart system, payment integration, and comprehensive email authentication.

## Features

- 🐟 **Fresh Seafood Catalog** - Browse and order from a variety of fresh fish
- 🛒 **Smart Cart System** - Session-based cart with real-time updates
- 💳 **Secure Payments** - Razorpay integration for safe transactions
- 📧 **Email Authentication** - OTP verification, password reset, security alerts
- 👥 **Multi-Role System** - Customer, Seller, Delivery, and Admin roles
- 📱 **Responsive Design** - Modern ocean-themed UI with smooth animations
- 📊 **Order Tracking** - Real-time order status and delivery updates

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the root directory with the following variables:

```env
# Flask Configuration
SESSION_SECRET=your-secret-key-here

# Razorpay Configuration
RAZORPAY_KEY_ID=rzp_test_your_key_here
RAZORPAY_KEY_SECRET=your_secret_here

# Email Configuration (Gmail SMTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

### 3. Gmail Setup for Email Features

To enable email functionality (OTP verification, password reset, security alerts):

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate an App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"
3. **Update .env file** with your Gmail and app password

### 4. Database Initialization

The app automatically creates and initializes the SQLite database on first run.

### 5. Run the Application

```bash
python app.py
```

Visit `http://localhost:5000` to access the application.

## Email Features

The platform includes a comprehensive email authentication system:

- **User Registration**: Email verification with OTP
- **Login Security**: OTP verification for enhanced security
- **Password Reset**: Secure token-based password recovery
- **Security Alerts**: New device login notifications

## Default Admin Account

- **Email**: admin@fish.com
- **Password**: admin123

## Project Structure

```
├── app.py                 # Main application entry point
├── artifacts/
│   └── fish-delivery/
│       └── app.py        # Core Flask application
├── templates/            # Jinja2 templates
│   ├── auth/            # Authentication pages
│   ├── emails/          # Email templates
│   └── *.html           # Main application pages
├── static/               # CSS, JS, images
├── requirements.txt      # Python dependencies
└── .env                 # Environment variables
```

## Technologies Used

- **Backend**: Flask, SQLite
- **Frontend**: HTML5, CSS3, JavaScript
- **Payments**: Razorpay
- **Email**: Flask-Mail, Gmail SMTP
- **Security**: OTP, Password hashing, Session management

## Security Features

- Password hashing with SHA-256
- OTP-based email verification
- Session-based authentication
- CSRF protection
- Secure password reset tokens
- New device login detection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.