from flask import flash,session as flask_session
from flask import render_template, redirect
from typing import List, Dict, Union
from datetime import datetime, timedelta
from functools import wraps
from sqlalchemy import Column
from collections import defaultdict, Counter
from email.mime.text import MIMEText
import random, smtplib ,json


type Info = List[Dict[str, Union[str, datetime]]]  #todo type def
type Result = tuple[str, list[dict[str, int]]]


try:
    with open('config.json', 'r') as f:
        data = json.load(f)
        if 'param' in data:
            params = data['param']

            # SMTP Configuration
            SMTP_SERVER = 'smtp.gmail.com'
            SMTP_PORT = 465
            SMTP_USERNAME = params['gmail-user']
            SMTP_PASSWORD = params['gmail-password']
            flask_session["send_email"] = True

except FileNotFoundError:
    flash("Email sending is disabled", "danger")
    flask_session["send_email"] = False


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
        if flask_session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def send_mail(email, purpose) -> None:
    """ Sends an email to the user. """ #check return
    if flask_session.get("send_email") is False:
        flash("send email option is disabled","danger")
        return
    otp = random.randint(100000, 999999)
    otp_info = {
        'value': otp,
        'timestamp': datetime.now(),
        'purpose': purpose,
        'email': email
    }
    msg = MIMEText(f"Your OTP is: {otp} \nPlease do not share your otp with others")
    msg['Subject'] = 'OTP Verification'
    msg['From'] = SMTP_USERNAME
    msg['To'] = email
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)

    flask_session["otp_info"] = otp_info
    return

def verify_email(user_otp):
    """ Verifies a user’s email address. """
    if flask_session.get("send_email") is False or flask_session.get('otp') is None:
        flash("verify email option is disabled", "danger")
        return None

    otp_data = flask_session.get("otp_info")

    if not otp_data:
        return False, "No OTP found"

    if datetime.now() - otp_data['timestamp'] > timedelta(minutes=10):
        return False, "OTP expired"

    try:
        if int(user_otp) != otp_data['value']:
            return False, "Invalid OTP"
    except ValueError:
        return False, "Invalid OTP format"

    return True, "OTP verified"


class VotingSystem:
    @staticmethod
    def approval(approval_ballots: list[list[str]] | 'Column', candidates: list[str] | 'Column') -> Result:
        """
        Determines the winner using the approval voting system.

        # Example:

        approval_ballots = [["Alice", "Bob"],["Alice"],["Bob", "Charlie"],["Charlie"],["Alice", "Charlie"]]

        candidates = ["Alice", "Bob", "Charlie"]

        return = "Alice", [{'Alice': 3, 'Bob': 2, 'Charlie': 3}]

        :param approval_ballots: List of ballots where each ballot is a list of approved candidates.
        :param candidates: List of all candidate names.
        :return: The candidate with the most approvals and a list containing the election results.
        """
        approval_count = Counter()

        # Count approvals for each candidate
        for ballot in approval_ballots:
            for candidate in ballot:
                if candidate in candidates:  # Only count valid candidates
                    approval_count[candidate] += 1

        # Store results in a list for table representation
        results = [{candidate: approval_count.get(candidate, 0) for candidate in candidates}]

        # Find the candidate with the highest approval count
        winner = max(results[0], key=lambda k: results[0].get(k, float('-inf')))
        return winner, results

    @staticmethod
    def borda_count(rankings: list[list[str]] | 'Column', candidates: list[str] | 'Column') -> tuple[str, list[dict[str, str | int]]]:
        """
        Determines the winner using the Borda Count voting system.

        Example Usage:
        rankings = [["Alice", "Bob", "Charlie"], ["Bob", "Charlie", "Alice"], ["Charlie", "Alice", "Bob"], ["Alice", "Charlie", "Bob"], ["Charlie", "Bob", "Alice"]]\n
        candidates = ["Alice", "Bob", "Charlie"]

        return = "Charlie", [{'Alice': 5, 'Bob': 4, 'Charlie': 6}]

        :param rankings: List of ranked ballots. Each ballot is a list of candidate preferences (first choice first).
        :param candidates: List of all candidate names.
        :return: The candidate with the most points and a list of round-by-round scores.
        """
        scores = {candidate: 0 for candidate in candidates}  # Initialize scores

        num_candidates = len(candidates)

        for ballot in rankings:
            seen = set()  # Ensure each ballot ranks candidates uniquely
            for rank, candidate in enumerate(ballot):
                if candidate in candidates and candidate not in seen:
                    scores[candidate] += num_candidates - rank - 1
                    seen.add(candidate)

        # Sort candidates by score (highest first)
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Assign ranks (handling ties)
        rank_table = []
        current_rank = 1
        for i, (candidate, score) in enumerate(sorted_scores):
            if i > 0 and score < sorted_scores[i - 1][1]:  # Lower score → increase rank
                current_rank = i + 1
            rank_table.append({"candidate": candidate, "total_score": score, "rank": f"{current_rank}{VotingSystem.ordinal_suffix(current_rank)}"})

        # Determine winner
        winner = sorted_scores[0][0]
        return winner, rank_table

    @staticmethod
    def condorcet(rankings: list[list[str]] | 'Column', candidates: list[str] | 'Column') -> tuple[str, list[list[str]]]:
        """
        Determines the winner using the Condorcet voting system.

        # Example Usage:
        rankings = [["A", "B", "C"],["B", "C", "A"],["C", "A", "B"],["A", "C", "B"],["C", "B", "A"]]

        candidates = ["A", "B", "C"]

        result= "C", [['vs. Candidate', 'A', 'B', 'C'], ['A', '—', '✅ (3–2)', '❌ (2–3)'], ['B', '❌ (2–3)', '—', '❌ (2–3)'], ['C', '✅ (3–2)', '✅ (3–2)', '—']]


        :param rankings: List of ranked ballots. Each ballot is a list of candidate preferences (first choice first).
        :param candidates: List of all candidate names.
        :return: The Condorcet winner (if one exists) and the pairwise comparison table.
        """
        pairwise_wins = defaultdict(lambda: defaultdict(int))

        # Tally pairwise wins
        for ballot in rankings:
            for i, candidate in enumerate(ballot):
                for j in range(i + 1, len(ballot)):
                    opponent = ballot[j]
                    if candidate in candidates and opponent in candidates:
                        pairwise_wins[candidate][opponent] += 1
                        break

        # Identify Condorcet winner
        for candidate in candidates:
            if all(pairwise_wins[candidate].get(opp, 0) > pairwise_wins[opp].get(candidate, 0)
                   for opp in candidates if opp != candidate):
                winner = candidate
                break
        else:
            winner = "No Condorcet Winner"

        # Build readable matrix
        matrix = []
        header = ["vs. Candidate"] + candidates
        matrix.append(header)

        for row_cand in candidates:
            row = [row_cand]
            for col_cand in candidates:
                if row_cand == col_cand:
                    cell = "—"
                else:
                    a = pairwise_wins[row_cand].get(col_cand, 0)
                    b = pairwise_wins[col_cand].get(row_cand, 0)
                    if a > b:
                        cell = f"✅ ({a}–{b})"
                    elif b > a:
                        cell = f"❌ ({a}–{b})"
                    else:
                        cell = f"🤝 ({a}–{b})"  # Tie
                row.append(cell)
            matrix.append(row)

        return winner, matrix

    @staticmethod
    def plurality(votes: list[str] | 'Column', candidates: list[str] | 'Column') -> Result:
        """
        Determines the winner using the plurality voting system.

        example:

        votes = ["Alice", "Bob", "Alice", "Charlie", "Bob", "Alice"]

        candidates = ["Alice", "Bob", "Charlie"]

        return = "Alice" , [{'Alice': 3, 'Bob': 2, 'Charlie': 1}]

        :param votes: List of candidate names selected by each voter.
        :param candidates: List of all candidate names.
        :return: The candidate with the most votes and a list containing the election results.
        """
        vote_count = Counter(votes)  # Count votes for each candidate

        # Filter only the candidates in the list
        results = [{candidate: vote_count.get(candidate, 0) for candidate in candidates}]

        # Find the candidate with the highest vote count
        winner = max(results[0], key=lambda k: results[0].get(k, float('-inf')))
        return winner, results

    @staticmethod
    def quadratic_voting(votes: list[dict[str, int]] | 'Column', candidates: list[str] | 'Column') -> tuple[str, list[dict[str, str]]]:
        """
        Determines the winner using the quadratic voting system.

        votes = [{"Alice": 9, "Bob": 4}, {"Alice": 4, "Charlie": 9}, {"Bob": 9, "Charlie": 1}, {"Alice": 1, "Charlie": 4}, {"Bob": 4, "Charlie": 9}]

        candidates = ["Alice", "Bob", "Charlie"]

        Results = "Charlie", [{'Alice': 3.9, 'Bob': 4.4, 'Charlie': 5.4}]

        :param votes: List of ballots where each ballot is a dictionary {candidate: allocated votes}.
        :param candidates: List of all candidate names.
        :return: The candidate with the highest total score and the election results.
        """
        scores = defaultdict(float)  # Sum of square roots (votes received)
        costs = defaultdict(int)     # Sum of squared votes (credits spent)

        # Calculate quadratic vote counts and total costs
        for ballot in votes:
            for candidate, allocated_votes in ballot.items():
                if candidate in candidates and allocated_votes > 0:
                    scores[candidate] += allocated_votes ** 0.5  # Quadratic sum for votes received
                    costs[candidate] += allocated_votes ** 2      # Quadratic cost calculation

        # Round vote counts for display
        results = {candidate: round(scores[candidate], 2) for candidate in candidates}

        # Sort candidates by votes received (handling ties)
        sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)

        # Assign ranks
        rank_table = []
        current_rank = 1
        for i, (candidate, votes_received) in enumerate(sorted_results):
            if i > 0 and votes_received < sorted_results[i - 1][1]:  # Lower score → increase rank
                current_rank = i + 1
            rank_table.append({
                "candidate_name": candidate,
                "votes": votes_received,
                "total_cost": costs[candidate],
                "rank": f"{current_rank}{VotingSystem.ordinal_suffix(current_rank)}"
            })

        # Determine the winner
        winner = sorted_results[0][0]
        return winner, rank_table

    @staticmethod
    def ranked_choice(ballots: list[list[str]] | 'Column', candidates: list[str] | 'Column') -> Result:
        """
        Determines the winner using Ranked-Choice Voting (RCV).

        Example:

        ballots = [ ["Alice", "Bob", "Charlie"], ["Alice", "Charlie", "Bob"], ["Bob", "Charlie", "Alice"], ["Charlie", "Alice", "Bob"], ["Charlie", "Bob", "Alice"], ["Bob", "Alice", "Charlie"]]\n

        candidates = ["Alice", "Bob", "Charlie"]

        return = "Charlie",  [{'Alice': 2, 'Bob': 2, 'Charlie': 2}, {'Alice': 2, 'Charlie': 4}, {'Charlie': 4}]


        :param ballots: List of ranked ballots. Each ballot is a list of candidate preferences (first choice first).
        :param candidates: List of all candidates.
        :return: Winner's name and a list of round-by-round vote distributions.
        """

        rounds = []
        remaining_candidates = set(candidates)
        total_voters = len(ballots)

        while True:
            # Count valid first-choice votes
            vote_count = Counter()
            for ballot in ballots:
                for choice in ballot:
                    if choice in remaining_candidates:
                        vote_count[choice] += 1
                        break

            # Add current round results
            current_round = {c: vote_count.get(c, 0) for c in remaining_candidates}
            rounds.append(current_round)

            # Check for majority winner
            if not vote_count:
                raise ValueError("No valid candidates remaining")

            max_votes = max(vote_count.values())
            if max_votes > total_voters / 2:
                return next(c for c, v in vote_count.items() if v == max_votes), rounds

            # Eliminate candidate with the least votes (break ties alphabetically)
            min_votes = min(vote_count.values())
            candidates_with_min = [c for c, v in vote_count.items() if v == min_votes]
            eliminated = min(candidates_with_min)

            remaining_candidates.remove(eliminated)
            if not remaining_candidates:
                raise ValueError("No candidates remaining after elimination")

    @staticmethod
    def range_voting(scores: list[dict[str, int]] | 'Column', candidates: list[str] | 'Column') -> tuple[str, list[dict[str, float]]]:
        """
        Determines the winner using the Range Voting system.

        # Example Usage:
        votes = [{"Alice": 9, "Bob": 6, "Charlie": 8},  {"Alice": 7, "Bob": 8, "Charlie": 6},  {"Alice": 10, "Bob": 7, "Charlie": 9}, {"Alice": 6, "Bob": 9, "Charlie": 7},  {"Alice": 8, "Bob": 7, "Charlie": 9}]
        candidates = ["Alice", "Bob", "Charlie"]

        result = "Alice", [{'Alice': 8.0, 'Bob': 7.4, 'Charlie': 7.8}]
        :param scores: List of ballots where each ballot is a dictionary {candidate: score}.
        :param candidates: List of all candidate names.
        :return: The candidate with the highest average score and election results.
        """
        total_scores = defaultdict(int)
        vote_counts = defaultdict(int)

        # Sum up scores and count the number of voters for each candidate
        for ballot in scores:
            for candidate, score in ballot.items():
                if candidate in candidates:
                    total_scores[candidate] += score
                    vote_counts[candidate] += 1

        # Calculate average scores for each candidate
        avg_scores = {candidate: (total_scores[candidate] / vote_counts[candidate]) if vote_counts[candidate] > 0 else 0
                      for candidate in candidates}

        # Store results for table representation
        results = [avg_scores]

        # Determine the winner (highest average score)
        winner = max(avg_scores, key=lambda k: avg_scores.get(k, float('-inf')))
        return winner, results

    @staticmethod
    def straight_ticket(votes: list[dict[str, str]] | 'Column', parties: list[str] | 'Column') -> Result:
        """
        Determines the winner using the straight-ticket voting system.

        Example Usage:
        # Example Usage:
        votes = [{"party": "Party A", "type": "straight"},{"party": "Party A", "type": "individual"},{"party": "Party A", "type": "straight"},{"party": "Party B", "type": "individual"},{"party": "Party B", "type": "straight"},{"party": "Party C", "type": "straight"},{"party": "Party C", "type": "straight"},{"party": "Party C", "type": "individual"}]

        parties = ["Party A", "Party B", "Party C"]

        return = "Party A",
        [{'Party': 'Party A', 'Straight Ticket Votes': 2, 'Individual Votes': 1, 'Total Votes': 3, 'Percentage of Total Votes': 37.5}
        {'Party': 'Party B', 'Straight Ticket Votes': 1, 'Individual Votes': 1, 'Total Votes': 2, 'Percentage of Total Votes': 25.0}
        {'Party': 'Party C', 'Straight Ticket Votes': 2, 'Individual Votes': 1, 'Total Votes': 3, 'Percentage of Total Votes': 37.5}]

        :param votes: List of party names selected by each voter.
        :param parties: List of all party names.
        :return: The party with the most votes and the election results.
        """
        straight_ticket_counts = defaultdict(int)
        individual_counts = defaultdict(int)

        # Count votes by type
        for vote in votes:
            if vote["type"] == "straight":
                straight_ticket_counts[vote["party"]] += 1
            else:
                individual_counts[vote["party"]] += 1

        # Prepare results
        results = []
        winner = ""
        max_votes = 0
        total_votes_all_parties = sum(straight_ticket_counts.values()) + sum(individual_counts.values())

        for party in parties:
            total_votes = straight_ticket_counts[party] + individual_counts[party]
            percentage = (total_votes / total_votes_all_parties) * 100 if total_votes_all_parties > 0 else 0

            results.append({
                "party": party,
                "straight_votes": straight_ticket_counts[party],
                "individual_votes": individual_counts[party],
                "total": total_votes,
                "percentage_Total": round(percentage, 2)
            })

            # Determine the party with the most votes
            if total_votes > max_votes:
                max_votes = total_votes
                winner = party

        return winner, results

    @staticmethod
    def ordinal_suffix(n: int) -> str:
        """Returns the ordinal suffix for a given number (e.g., 1st, 2nd, 3rd)."""
        if 10 <= n % 100 <= 20:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
