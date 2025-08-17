import os
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from models import Account, License, Device
from utils import is_valid_key, parse_expiration_date, is_account_expired
from datetime import datetime

app = Flask(__name__)

# ====================== Database Configuration ======================
# PostgreSQL connection with your provided credentials
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://fireauth:P4dUuwaKa9N7FjHxKuhxIcsW3BLebeNL@dpg-d2gvrqn5r7bs73fi3peg-a.ohio-postgres.render.com/fireauth'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_size': 10,
    'max_overflow': 20,
}

db.init_app(app)

# ====================== Security Configuration ======================
# Your provided security keys
ADMIN_KEY = 'WOLFXITER4567899989877779979877987979'
CLIENT_KEY = 'WOLFXITER48888887777799987987498494555555'
SECRET_KEY = generate_password_hash(ADMIN_KEY + CLIENT_KEY)  # Derived secret for sessions

app.config['SECRET_KEY'] = SECRET_KEY

# ====================== Database Initialization ======================
def initialize_database():
    """Ensure all database tables are created and connection works"""
    with app.app_context():
        try:
            db.create_all()
            # Test connection with a simple query
            db.session.execute('SELECT 1')
            print("✅ Database connection successful and tables initialized!")
        except Exception as e:
            print(f"❌ Database initialization failed: {str(e)}")
            raise

# Initialize immediately when app starts
initialize_database()

# ====================== Security Enhancements ======================
def log_security_event(action, ip_address):
    """Log security-relevant events"""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[SECURITY] {timestamp} | {action} | IP: {ip_address}")

# ====================== Updated Routes with Enhanced Security ======================
@app.route('/login', methods=['GET'])
def login():
    username = request.args.get('Username')
    password = request.args.get('Password')
    client_key = request.args.get('Key')
    ip_address = request.remote_addr

    # Enhanced key validation
    if not is_valid_key(client_key, CLIENT_KEY):
        log_security_event("Invalid client key attempt", ip_address)
        return jsonify({
            "status": "failure",
            "reason": "invalid credentials",
            "timestamp": datetime.utcnow().isoformat()
        }), 401

    account = Account.query.filter_by(username=username).first()
    
    # Account checks with security logging
    if not account:
        log_security_event("Invalid username attempt", ip_address)
        return jsonify({
            "status": "failure",
            "reason": "invalid credentials",
            "timestamp": datetime.utcnow().isoformat()
        }), 404
    
    if is_account_expired(account):
        log_security_event("Expired account access attempt", ip_address)
        return jsonify({
            "status": "failure",
            "reason": "account expired",
            "timestamp": datetime.utcnow().isoformat()
        }), 403

    # Track device/IP with security logging
    device = Device.query.filter_by(account_id=account.id, ip_address=ip_address).first()
    if not device:
        if len(account.devices) >= account.max_users:
            log_security_event("Device limit reached", ip_address)
            return jsonify({
                "status": "failure",
                "reason": "device limit reached",
                "timestamp": datetime.utcnow().isoformat()
            }), 403
        new_device = Device(ip_address=ip_address, account_id=account.id)
        db.session.add(new_device)
        db.session.commit()
        log_security_event("New device registered", ip_address)

    return jsonify({
        "status": "success",
        "username": account.username,
        "created_date": account.created_date.isoformat(),
        "expiration_date": account.expiration_date.isoformat(),
        "devices": [d.ip_address for d in account.devices],
        "timestamp": datetime.utcnow().isoformat()
    }), 200

# [Include all your other routes with similar security enhancements]

if __name__ == '__main__':
    # Production configuration - disable debug mode
    app.run(host='0.0.0.0', port=10000, debug=False)
