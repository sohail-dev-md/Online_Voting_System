from flask import redirect, render_template, session
from random import randint
from typing import List, Dict, Set
from datetime import datetime, timedelta
from functools import wraps
from collections import Counter
from email.mime.text import MIMEText
import json
import smtplib

with open('config.json', 'r') as f:
    params = json.load(f)['param']


SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465
SMTP_USERNAME = params['gmail-user']
SMTP_PASSWORD = params['gmail-password']

def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


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
# ------------------------------------------------------------------------------------------
class VotingSystem:

    @staticmethod
    def plurality_winner(votes: List[str], candidates: List[str]) -> str:
        """
        Determines the winner using the plurality voting system.

        :param votes: List of candidate names selected by each voter.
        :param candidates: List of all candidate names.
        :return: The candidate with the most votes.
        """
        vote_counts = Counter(votes)
        return vote_counts.most_common(1)[0][0]

    @staticmethod
    def ranked_choice_winner(votes: List[List[str]], candidates: List[str]) -> str:
        """
        Determines the winner using the ranked-choice voting system.

        :param votes: List of lists, each sublist is a voter's ranking of candidates.
        :param candidates: List of all candidate names.
        :return: The winner based on instant runoff rules.
        """
        while True:
            first_choices = [vote[0] for vote in votes if vote]
            vote_counts = Counter(first_choices)
            total_votes = len(votes)
            for candidate, count in vote_counts.items():
                if count > total_votes / 2:
                    return candidate
            least_candidate = min(vote_counts, key=vote_counts.get)
            votes = [[candidate for candidate in vote if candidate != least_candidate] for vote in votes]

    @staticmethod
    def approval_winner(votes: List[Set[str]], candidates: List[str]) -> str:
        """
        Determines the winner using the approval voting system.

        :param votes: List of sets, each set contains approved candidates by a voter.
        :param candidates: List of all candidate names.
        :return: The candidate with the most approvals.
        """
        vote_counts = Counter()
        for vote in votes:
            vote_counts.update(vote)
        return vote_counts.most_common(1)[0][0]

    @staticmethod
    def straight_ticket_winner(votes: List[str], slates: Dict[str, List[str]], candidates: List[str]) -> List[str]:
        """
        Determines the winners using the straight ticket voting system.

        :param votes: List of selected slates by each voter.
        :param slates: Dictionary mapping slate names to lists of candidates.
        :param candidates: List of all candidate names.
        :return: List of candidates who receive votes based on slate selections.
        """
        slate_counts = Counter(votes)
        candidate_counts = Counter()
        for slate, count in slate_counts.items():
            for candidate in slates.get(slate, []):
                candidate_counts[candidate] += count
        return [candidate for candidate, count in candidate_counts.most_common()]

    @staticmethod
    def borda_count_winner(votes: List[List[str]], candidates: List[str]) -> str:
        """
        Determines the winner using the Borda count voting system.

        :param votes: List of lists, each sublist is a voter's ranking of candidates.
        :param candidates: List of all candidate names.
        :return: The candidate with the highest Borda score.
        """
        points = {candidate: 0 for candidate in candidates}
        rank_value = len(candidates) - 1
        for vote in votes:
            for i, candidate in enumerate(vote):
                points[candidate] += rank_value - i
        return max(points, key=points.get)

    @staticmethod
    def quadratic_voting_winner(votes: Dict[str, int], candidates: List[str]) -> str:
        """
        Determines the winner using the quadratic voting system.

        :param votes: Dictionary where keys are candidates and values are the number of votes cast for them.
        :param candidates: List of all candidate names.
        :return: The candidate with the highest votes after applying quadratic cost.
        """
        # Assuming votes are already adjusted for quadratic cost
        return max(votes, key=votes.get)

    @staticmethod
    def condorcet_winner(votes: List[List[str]], candidates: List[str]) -> str:
        """
        Determines the winner using the Condorcet method.

        :param votes: List of lists, each sublist is a voter's ranking of candidates.
        :param candidates: List of all candidate names.
        :return: The Condorcet winner if one exists.
        """
        pairwise = {candidate: {other: 0 for other in candidates if other != candidate} for candidate in candidates}
        for vote in votes:
            for i, candidate in enumerate(vote):
                for j in range(i+1, len(vote)):
                    pairwise[candidate][vote[j]] += 1
        for candidate in candidates:
            if all(pairwise[candidate][other] > pairwise[other][candidate] for other in candidates if other != candidate):
                return candidate
        return ""

    @staticmethod
    def range_voting_winner(votes: Dict[str, List[int]], candidates: List[str]) -> str:
        """
        Determines the winner using the range voting system.

        :param votes: Dictionary where keys are candidates and values are lists of ratings from voters.
        :param candidates: List of all candidate names.
        :return: The candidate with the highest average rating.
        """
        averages = {candidate: sum(ratings)/len(ratings) for candidate, ratings in votes.items()}
        return max(averages, key=averages.get)
