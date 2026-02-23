from flask import Flask, flash, redirect, render_template, request, session, jsonify, send_from_directory, url_for, abort
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename, safe_join
from datetime import datetime, timedelta
from flask_session import Session
from random import randint
import os
import json
import smtplib
from email.mime.text import MIMEText
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from cs50 import SQL


from helpers import apology, login_required, generate_and_send_otp, verify_otp

app = Flask(__name__)
# Configure session to use filesystem (instead of signed cookies)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///ovs.db")

with open('config.json', 'r') as f:
    params = json.load(f)['param']

# SMTP Configuration
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465
SMTP_USERNAME = params['gmail-user']
SMTP_PASSWORD = params['gmail-password']


# Define where to store uploaded files
UPLOAD_FOLDER = os.path.join(app.root_path, 'static/uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit file size to 16 MB
Session(app)


# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


options = ["csv"]
# Rate Limiter
limiter = Limiter(app=app, key_func=get_remote_address)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Validation logic
        if not all([request.form.get('username'),
                   request.form.get('email'),
                   request.form.get('password')]):
            return apology("Missing required fields")

        if request.form.get('password') != request.form.get('confirmation'):
            return apology("Passwords don't match")

        # Query database for username or email
        rows = db.execute(
            "SELECT * FROM users WHERE Username = ? OR Email = ?", request.form.get("username"), request.form.get("email")
        )

        # Ensure username/email exists and password is correct
        if len(rows) != 0:
            return apology("invalid username or email or password", 403)

        # Store registration data
        session['reg_data'] = {
            'username': request.form.get('username'),
            'email': request.form.get('email'),
            'password_hash': generate_password_hash(request.form.get('password')),
            'age': request.form.get('age')
        }

        generate_and_send_otp(request.form.get('email'), 'registration')
        flash("OTP sent to your email", "success")
        return redirect("/verify_otp")

    return render_template("register.html")

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get('email')
        if not email:
            flash("Please enter your email", "danger")
            return redirect(url_for('forgotpassword'))

        session['reset_email'] = email
        generate_and_send_otp(email, 'password_reset')
        flash("OTP sent to your email", "success")
        return redirect("/verify_otp")

    return render_template("forgotpassword.html")


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if 'reset_email' not in session:
        flash("Session expired", "danger")
        return redirect(url_for('forgot_password'))

    if request.method == "POST":
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')

        if password != confirmation:
            flash("Passwords don't match", "danger")
            return render_template("reset_password.html")

        # Update password
        db.execute(
            "UPDATE users SET hash = ? WHERE email = ?",
            generate_password_hash(password),
            session['reset_email']
        )

        session.clear()
        flash("Password updated successfully!", "success")
        return redirect("/login")

    return render_template("reset_password.html")


@app.route("/verify_otp", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def verify_otp():
    if request.method == "POST":
        success, message = verify_otp(request.form.get('otp'))
        if not success:
            flash(message, "danger")
            return render_template("verify_otp.html")

        otp_data = session.get('otp')
        if otp_data['purpose'] == 'registration':
            # Complete registration
            reg_data = session.get('reg_data')
            if not reg_data:
                flash("Session expired", "danger")
                return redirect(url_for('register'))

            None # Check existing user
            if db.execute("SELECT * FROM users WHERE email = ?", reg_data['email']):
                session.clear()
                flash("Email already exists", "danger")
                return redirect("/login")

            # Create new user
            db.execute(
                "INSERT INTO users (username, email, hash, age) VALUES (?, ?, ?, ?)",
                reg_data['username'], reg_data['email'],
                reg_data['password_hash'], reg_data['age']
            )

            session.clear()
            flash("Registration successful!", "success")
            return redirect("/login")

        elif otp_data['purpose'] == 'password_reset':
            return redirect("/reset-password")

    return render_template("verify_otp.html")



def generate_and_send_otp(email, purpose):
    """Generate OTP and send email"""
    otp = randint(100000, 999999)
    session['otp'] = {
        'value': otp,
        'timestamp': datetime.now(),
        'purpose': purpose,
        'email': email
    }

    msg = MIMEText(f"Your OTP is: {otp} \n Please do not share your otp with others")
    msg['Subject'] = 'OTP Verification'
    msg['From'] = SMTP_USERNAME
    msg['To'] = email

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)

def verify_otp(user_otp):
    """Validate OTP from user"""
    otp_data = session.get('otp')

    if not otp_data:
        return False, "No OTP found"

    if datetime.now() - otp_data['timestamp'] > timedelta(minutes=5):
        return False, "OTP expired"

    try:
        if int(user_otp) != otp_data['value']:
            return False, "Invalid OTP"
    except ValueError:
        return False, "Invalid OTP format"

    return True, "OTP verified"



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure either username or email was submitted
        if not request.form.get("username"):
            return apology("must provide username or Email", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username or email
        rows = db.execute(
            "SELECT * FROM users WHERE Username = ? OR Email = ?", request.form.get("username"), request.form.get("username")
        )

        # Ensure username/email exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["Hash"], request.form.get("password")
        ):
            return apology("invalid username or email or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["ID"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/change-password", methods=["POST", "GET"])
@login_required
def change_password():
    """Change user's password"""

    if request.method == "POST":
        # Get the current password
        password = request.form.get("password")
        # Get the new password
        new_password = request.form.get("new_password")
        # Get the confirmation password
        confirmation = request.form.get("confirmation")

        # Query database for the current user's data
        rows = db.execute("SELECT * FROM users WHERE ID= ?", session['reg_data']["user_id"])

        # Ensure all password fields are submitted
        if confirmation == "" or password == "" or new_password == "":
            return apology("must provide password")

        # Ensure current password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["Hash"], password):
            return apology("invalid username and/or password")

        # Ensure new password matches confirmation
        if new_password != confirmation:
            return apology("confirmation password must be same as password")

        # Update the password in the database
        db.execute(
            "UPDATE users SET Hash = ? WHERE ID= ?", generate_password_hash(
                new_password), session["user_id"]
        )

        # Forget any user_id
        session.clear()

        # Redirect user to login form
        return redirect("/")

    else:
        info = db.execute("SELECT * FROM users WHERE ID= ?", ["user_id"])[0]
        return render_template("changepassword.html", info=info)


@app.route('/info')
def info():
    if session["user_id"]:
        info = db.execute("SELECT * FROM users WHERE ID= ?", ["user_id"])[0]
        return render_template('info.html',info=info)
    else:
        return render_template("info.html")


@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files or 'user_id' not in session:
        return jsonify({'error': 'No file or user_id part'}), 400

    file = request.files['file']
    user_id = session.get("user_id") or abort(401)

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(f"{user_id}.png")
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    return jsonify({'success': 'File uploaded successfully', 'filename': filename})


# Download route
@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return send_from_directory(app.config['UPLOAD_FOLDER'], "default.jpeg")


@app.route('/', methods=["POST", "GET"])
@login_required
def register_project():
    # return render_template('nav.html',methods=options, info=info, user_id = session['reg_data']["user_id"])
    return render_template('election_registration.html')




if __name__ == "__main__":
    app.run(debug=True)
