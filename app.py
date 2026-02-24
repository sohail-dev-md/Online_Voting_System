from flask import Flask, flash, request, Session, jsonify, render_template, redirect, abort, send_from_directory, url_for, session as flask_session
from random import randint, choice
from datetime import timedelta, datetime
from sqlalchemy import create_engine
from flask_limiter import Limiter
from sqlalchemy.orm import declarative_base, sessionmaker
from werkzeug.utils import secure_filename
from flask_limiter.util import get_remote_address
import os


db = "sqlite:///ovs.db"

engine = create_engine(db)
Base = declarative_base()
db_Session = sessionmaker(bind=engine)
db_session = db_Session()

# Import models after initializing db
from models import User, Election
Base.metadata.create_all(engine)

app = Flask(__name__)
# Configure session to use filesystem (instead of signed cookies) TODO
app.config['SECRET_KEY'] = 'Real_final_final_0.12_version'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


# Define where to store uploaded files
UPLOAD_FOLDER = os.path.join(app.root_path, 'static/uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit file size to 16 MB
Session(app)

from helpers import apology, login_required, send_mail, verify_email

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Rate Limiter
options = ["csv"]
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

        if not User.available_username(username=str(request.form.get('username'))) and not User.available_email(email=str(request.form.get('email'))):
            return redirect("/register")

        if flask_session.get("send_email"):
            # Store registration data
            flask_session['reg_data'] = {
                'username': request.form.get('username'),
                'email': request.form.get('email'),
                'age': request.form.get('age'),
                'password': request.form.get('password')
            }

            send_mail(email=request.form.get('email'), purpose="Register")
            flash("OTP sent to your email", "success")
            return redirect("/verify_otp")

        # Query database for username or email
        user: User = User(username=request.form.get('username'),email=request.form.get('email'),age=request.form.get("age"),password=request.form.get("password"))

        # Store registration data
        flask_session['user_id'] = user.id

        flash("Registered successfully!", "success")

        # Add user to database
        db_session.add(user)
        db_session.commit()

    return render_template("register.html")


@app.route("/logout")
def logout():
    """Log user out"""
    flask_session.clear()
    return redirect("/")


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get('email') #todo
        user_id = User.query.filter_by(email=email).one_or_none().get("id", None)
        if not email or not user_id:
            flash("Please enter valid email", "danger")
            return redirect("/forgot_password")

        flask_session['reset_email'] = email
        flask_session['user_id'] = user_id
        send_mail(email, 'password_reset')
        flash("OTP sent to your email", "success")
        return redirect("/verify_otp")

    return render_template("forgot_password.html")


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():   # is this the next step for the forgot_password after otp verification
    if 'reset_email' not in flask_session:
        flash("Session expired", "danger")
        return redirect("/forgot_password")

    if request.method == "POST":
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')

        if password != confirmation:
            flash("Passwords don't match", "danger")
            return render_template("reset_password.html")

        user:User = User.get_user(user_id=int(flask_session.get('user_id')))    # user_id was set in forgot_password route
        # Update password
        user.update_password(new_password=str(password))

        flash("Password updated successfully!", "success")
        return redirect("/logout")

    return render_template("reset_password.html")


@app.route("/verify_otp", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def verify_otp():
    if request.method == "POST":
        success, message = verify_email(request.form.get('otp'))
        if not success:
            flash(message, "danger")
            return render_template("verify_otp.html")

        otp_data:dict = flask_session.get('otp')
        if otp_data['purpose'] == 'registration':
            # Complete registration
            reg_data = flask_session.get('reg_data')
            if not reg_data:
                flash("Session expired", "danger")
                return redirect("/register")

            user:User = User(
                username=flask_session['reg_data']['username'],
                email=flask_session['reg_data']['email'],
                age=flask_session['reg_data']['age'],
                password=flask_session['reg_data']['password']
            )

            flask_session.pop('reg_data',None)

            # Add user to database
            db_session.add(user)
            db_session.commit()

            flash("Registration successful!", "success")
            return redirect("/")

        elif otp_data['purpose'] == 'password_reset':
            return redirect("/reset_password")

    return render_template("verify_otp.html")


@app.route("/change_password", methods=["POST", "GET"])
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
        user:User = User.get_user(int(flask_session.get('user_id')))

        # Ensure all password fields are submitted
        if confirmation == "" or password == "" or new_password == "":
            return apology("must provide password")

        # Ensure current password is correct
        if not user and not user.check_password(password=str(password)):
            return apology("invalid username and/or password")

        # Ensure new password matches confirmation
        if new_password != confirmation:
            return apology("confirmation password must be same as password")

        # Update the password in the database
        user.update_password(new_password=password)

        # Forget any user_id
        flask_session.clear()

        # Redirect user to login form
        return redirect("/")

    else:
        # wtf is this doing here? todo
        return render_template("change_password.html", profile_info=User.user_profile(flask_session.get("user_id")))


@app.route('/info')
def info():
    if flask_session.get("user_id", None) is not None:
        return render_template('info.html', profile_info=User.user_profile(flask_session.get("user_id")))
    else:
        return render_template("info.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id ; just to be shore
    flask_session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure either username or email was submitted
        if not request.form.get("username"):
            return apology("must provide username or Email", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username or email
        user = User.authenticate_user(username=str(request.form.get("username")),password=str(request.form.get("password")))

        # Ensure username/email exists and password is correct
        if not user:
            return apology("invalid username or email or password", 403)

        # Remember which user has logged in
        flask_session["user_id"] = user.id

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files or 'user_id' not in flask_session:
        return jsonify({'error': 'No file or user_id part'}), 400

    file = request.files['file']
    user_id = flask_session.get("user_id") or abort(401)

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


@login_required
@app.route('/')
def index():
    user = User.get_user(flask_session.get("user_id"))
    search = user.hosted_elections + user.participated_elections
    if not search:
        elections = []
    else:
        elections =[election for election in Election.private_search(search) or Election.public_search(search)]

    return render_template("history.html",election_info=elections)



@login_required
@app.route('/create_election', methods=["GET", "POST"])
def create_election():
    if request.method == "POST":
        data = request.json
        if not data:
            flash("Invalid JSON data","error")
            return redirect('/create_election')

        required_fields: list[str] = ["title", "end_of_election", "type_of_election", "key"]

        missing_fields: list = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            flash(f"Missing fields: {"".join(missing_fields)}", "error")
            return redirect('/create_election')

        if not data.get("candidates") and not (data.get("end_of_candidate_selection") or data.get("start_of_election")):
            flash("Candidate info is incomplete","error")
            return redirect('/create_election')

        # todo __init__(**data) for election
        election = Election(data=data)
        User.get_user(flask_session.get("user_id")).hosted_elections.append(election.key)
        db_session.add(election)
        db_session.commit()
        # jsonify({'success': f'Election { data.get("title") } created successfully', 'election' : data.get("title")})
        flash(f'Election { data.get("title") } created successfully',"success")
        return redirect("/")

    return render_template("create_election.html", profile_info=User.user_profile(flask_session.get("user_id")))


@login_required
@app.route("/generate_key")
def generate_key():
    length = randint(8,13)
    key = []
    helper = "123456789!#?$%&@ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    while len(key) < length:
        key.append(choice(helper))

    key = "".join(key)

    if not Election.query.filter_by(key=key).count():
        return key
    else:
        return redirect("/generate_key")

@app.route("/register_candidate/<election_key>", methods=["GET", "POST"])
@login_required
def register_candidate(election_key):
    election = Election.get_election(election_key=election_key)
    if not election:
        flash("Election not found.", "danger")
        return redirect("/")

    user = User.get_user(flask_session.get("user_id"))
    if not user:
        flash("User not found.", "danger")
        return redirect("/logout")

    # Ensure we're dealing with actual Python boolean values from fetched instance
    is_active = election.is_active  # This should now be a Python bool
    start_candidate_selection = election.start_of_candidate_selection
    end_candidate_selection = election.end_of_candidate_selection

    if not isinstance(is_active, bool):
        is_active = bool(is_active)

    if not is_active:
        flash("Election is not active.", "warning")
        return redirect("/")

    if not start_candidate_selection or not end_candidate_selection:
        flash("Candidate registration period is not set.", "warning")
        return redirect("/")

    now = datetime.now()
    if not (start_candidate_selection <= now < end_candidate_selection):
        flash("Candidate registration is not open at this time.", "warning")
        return redirect("/")

    if request.method == "POST":
        candidate_name = request.form.get("candidate", "").strip()
        if not candidate_name:
            flash("Candidate name cannot be empty.", "danger")
            return redirect(url_for("register_candidate", election_key=election_key))

        # Prevent duplicate candidates
        if election.candidate_exists(candidate_name):
            flash(f"'{candidate_name}' is already registered as a candidate.", "warning")
            return redirect(url_for("register_candidate", election_key=election_key))

        try:
            election.add_candidates(candidate_name)
            db_session.commit()
            flash(f"'{candidate_name}' has been successfully registered!", "success")
            return redirect("host_election")  # Or wherever appropriate
        except Exception as e:
            db_session.rollback()
            flash("An error occurred while registering the candidate.", "danger")
            print(f"Error: {e}")

    # GET request: show the form
    return render_template(
        "register_candidate.html",
        election=election.election_info(),
        profile_info=User.user_profile(flask_session.get("user_id"))
    )

@app.route("/host_election/<election_key>", methods=["GET", "POST"])
@login_required
def host_election(election_key):
    user = User.get_user(flask_session.get("user_id"))
    election = Election.get_election(election_key=election_key)

    if not election:
        flash("Election not found.", "danger")
        return redirect(url_for("index"))

    # Redirect if user already participated or hosted this election
    if election_key in (user.participated_elections or user.hosted_elections):
        return redirect(url_for("election_results", election_key=election_key))

    if request.method == "POST":
        vote_data = request.get_json(silent=True)

        if not vote_data:
            flash("Please submit a valid vote.", "danger")
            return render_template(
                "host_election.html",
                election=election.election_info(),
                profile_info=User.user_profile(flask_session.get("user_id"))
            )

        try:
            election.add_vote(vote=vote_data)
            user.participated_elections.append(election_key)
            db_session.commit()
            flash("Your vote has been recorded successfully!", "success")
            return redirect(url_for("election_results", election_key=election_key))
        except Exception as e:
            db_session.rollback()
            flash("An error occurred while recording your vote.", "danger")
            print(f"Vote error: {e}")
            return redirect(url_for("host_election", election_key=election_key))

    # GET request: show the form
    return render_template(
        "host_election.html",
        election=election.election_info(),
        profile_info=User.user_profile(flask_session.get("user_id"))
    )


@app.route('/election/<election_key>/results')
@login_required
def election_results(election_key):
    user = User.get_user(flask_session.get("user_id"))
    election = Election.get_election(election_key=election_key)

    if not election:
        flash("Election not found.", "danger")
        return redirect(url_for("index"))

    if election_key not in (user.participated_elections or user.hosted_elections):
        flash("You cannot view results until you participate.", "warning")
        return redirect(url_for("host_election", election_key=election_key))

    winner, result = election.winner, election.result

    if not winner:
        flash("The election is still ongoing or no votes have been cast.", "info")
        return redirect(url_for("dashboard"))  # Or wherever appropriate

    flash(f"The winner is {winner}", "success")
    return render_template(
        "result.html",
        results={"winner": winner, "result": result},
        profile_info=User.user_profile(flask_session.get("user_id"))
    )

@login_required
@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        search = request.form.get("search")

        if not search:
            elections = Election.random_election(no_of_elections=10)
        else:
            elections =[election for election in Election.private_search(search) or Election.public_search(search)]

        return render_template("search.html",election_info=elections)

    return render_template("search.html",election_info=Election.random_election(no_of_elections=10))


if __name__ == '__main__':
    app.run(debug=True)
