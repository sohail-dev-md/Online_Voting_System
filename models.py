from app import Base, db_session
from flask import flash, session as flask_session
from helpers import VotingSystem, Info
from datetime import datetime
from sqlalchemy import relationship, func, Column, String, Integer, ForeignKey, Boolean, DateTime, JSON, Table, or_, and_
from werkzeug.security import check_password_hash, generate_password_hash
import random

# Many-to-Many Association Table between users and elections
user_election = Table(
    "user_election", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("election_id", Integer, ForeignKey("elections.id"), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    age = Column(Integer, nullable=False)
    password = Column(String, nullable=False)

    # Relationships
    participated_elections = relationship(
        "Election", secondary=user_election, back_populates="participants"
    )
    hosted_elections = relationship("Election", back_populates="creator")


    def __init__(self, username, email, age, password):
        """ Initializes a new user with a hashed password for security. """
        self.username = username
        self.email = email
        self.age = age
        self.update_password(password)


    def check_password(self, password: str) -> bool:
        """ Verifies if the provided password matches the stored hashed password. """
        if not str(self.password):
            return False

        return check_password_hash(str(self.password), password)


    def update_password(self, new_password: str) -> None:
        """ Updates the user's password by hashing the new password. """
        self.password = generate_password_hash(new_password)
        db_session.commit()

    @classmethod
    def available_username(cls, username: str) -> bool:
        """
        Checks whether a given username is available for registration.
        """
        return cls.query.filter(cls.username == username).one_or_none() is None

    @classmethod
    def available_email(cls, email: str) -> bool:
        """
        Checks whether a given username is available for registration.
        """
        return cls.query.filter(cls.email == email).one_or_none() is None

    @classmethod
    def get_user(cls, user_id: int):
        """
        Fetches a user instance by user ID.
        """
        return cls.query.filter_by(id=user_id).first()

    @classmethod
    def authenticate_user(cls, username: str, password: str):
        """
        Authenticates a user for login. Returns a user instance if successful, otherwise an error message.
        """
        user = cls.query.filter_by(username=username).first()
        if user is None:
            flash("User not found")
            return

        if user.check_password(password) is False:
            flash("Incorrect Password")
            return
        return user

    @classmethod
    def user_profile(cls, user_id: int):
        """Fetch user profile"""
        user = cls.query.filter_by(id=user_id).first()

        if not user:
            flash("User not found")
            return

        user_profile = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "age": user.age,
            "participated_elections": len(user.participated_elections),
            "hosted_elections": len(user.hosted_elections)
        }

        return user_profile


class Election(Base):

    __tablename__ = "elections"

    id = Column(Integer, primary_key=True)
    creators_id = Column(String, ForeignKey("users.username"), nullable=False)
    title = Column(String, nullable=False)
    explanation = Column(String, default="No explanation provided.")
    type_of_election = Column(String, nullable=False, default="plurality")
    key = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    visibility = Column(String, default="public")

    start_of_candidate_selection = Column(DateTime)
    end_of_candidate_selection = Column(DateTime)
    start_of_election = Column(DateTime, default=datetime.now())
    end_of_election = Column(DateTime, nullable=False)

    candidates = Column(JSON, default=list)
    votes = Column(JSON, default=list)
    result = Column(JSON, default=list)
    winner = Column(String, default="Not declared")

    # Relationships
    user_election = Table(
        "user_election", Base.metadata,
        Column("username", String, ForeignKey("users.username"), primary_key=True),
        Column("election_id", Integer, ForeignKey("elections.id"), primary_key=True)
    )

    def __init__(self, **data):

        self.creators_id = User.get_user(flask_session.get("user_id")).username
        if self.check_key(data.get("key",None)):
            self.key = data.get("key")
            data.pop("key")
        else:
            return # or make the key using randomizer

        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

        pass


    @classmethod
    def get_election(cls,election_key):
        return cls.query.filter_by(key=election_key).one_or_none()

    def add_candidates(self, candidate):
        """
        adds the new candidate to the end of list of candidates
        :param candidate: string
        :return: None
        """
        if candidate not in self.candidates:
            self.candidates.append(candidate)
        else:
            flash(f"candidate name {candidate} is taken","warning") #todo

    def update_result(self) -> None:
        """ Computes the winner and election results based on the election type using different voting methods. """
        if str(self.type_of_election) == 'plurality':
            winner, results = VotingSystem.plurality(votes=self.votes, candidates=self.candidates)

        elif str(self.type_of_election) == 'range_voting':
            winner, results = VotingSystem.range_voting(scores=self.votes, candidates=self.candidates)

        elif str(self.type_of_election) == 'quadratic_voting':
            winner, results = VotingSystem.quadratic_voting(votes=self.votes, candidates=self.candidates)

        elif str(self.type_of_election) == 'approval':
            winner, results = VotingSystem.approval(approval_ballots=self.votes, candidates=self.candidates)

        elif str(self.type_of_election) == 'condorcet':
            winner, results = VotingSystem.condorcet(rankings=self.votes, candidates=self.candidates)

        elif str(self.type_of_election) == 'borda_count':
            winner, results = VotingSystem.borda_count(rankings=self.votes, candidates=self.candidates)

        elif str(self.type_of_election) == 'ranked_choice':
            winner, results = VotingSystem.ranked_choice(ballots=self.votes, candidates=self.candidates)

        elif str(self.type_of_election) == 'straight_ticket':
            winner, results = VotingSystem.straight_ticket(votes=self.votes, parties=self.candidates)

        else:
            return None # (f"Unsupported voting system type: {self.type_of_election}", "danger")

        self.winner = winner
        self.result = results

    # noinspection PyTypeChecker todo
    def graph_info(self) -> list:
        """ generate election-related graph data. """ #TODO nope do it so that each g_table can be set table info for the graph
        total_votes = len(self.votes)
        g_table:list = []

        if str(self.type_of_election) == "plurality":
            g_table.append(["Candidate", "Votes", "Percentage"])
            for candidate, votes in self.result[0].items():
                percentage = round((float(votes) / total_votes) * 100, 2)
                g_table.append([candidate, votes, f"{percentage}%"])

        elif str(self.type_of_election) == "approval":
            g_table.append(["Candidate", "Approvals", "Percentage"])
            for candidate, approvals in self.result[0].items():
                percentage = round((float(approvals) / total_votes) * 100, 2)
                g_table.append([candidate, approvals, f"{percentage}%"])

        elif str(self.type_of_election) == "straight_ticket":
            g_table.append(['Party', 'Straight Votes', 'Individual Votes', 'Total', 'Percentage'])
            for entry in self.result:
                party = entry.get('party', 'Unknown')
                straight = entry.get('straight_votes', 0)
                individual = entry.get('individual_votes', 0)
                total = entry.get('total',0)
                percentage = entry.get('percentage_Total',0)
                g_table.append([party, straight, individual, total, f"{percentage}%"])


        elif str(self.type_of_election) == "borda_count":
            g_table.append(["Candidate", "Total Score", "Rank"])
            for entry in self.result:
                candidate = entry.get('candidate', 'Unknown')
                score = entry.get('total_score', 0)
                rank = entry.get('rank',0)
                g_table.append([candidate, score, rank])


        elif str(self.type_of_election) == "range_voting":
            g_table = [["Candidate_name", "Total_Score", "Avg_score"]]

            for key,value in self.result[0].items():
                g_table.append([key, value*total_votes, value])

        elif str(self.type_of_election) == "quadratic_voting":
            g_table.append(["Candidate_name", "Votes Received", "Total Cost (Credits)", "Rank"])
            for entry in self.result:
                candidate = entry.get('candidate_name', 'Unknown')
                votes = entry.get('votes', 0)
                cost = entry.get('total_cost',0)
                rank = entry.get('rank',0)
                g_table.append([candidate, votes, cost, rank])

        elif str(self.type_of_election) == "ranked_choice":
            g_table = [["Round"] + [i for i in self.candidates]]
            for round_number, entry in enumerate(self.result):
                round_data = []

                for candidate in self.candidates:
                    round_data.append(entry.get(candidate, 'Eliminated'))

                g_table.append([round_number] + round_data)


        elif str(self.type_of_election) == "condorcet":
            g_table = self.result

        return g_table

    def add_vote(self, vote) -> None:
        """
        Adds a vote to the election and updates the results.

        :param vote: candidate names selected by each voter
        """
        self.votes.append(vote)
        self.update_result()
        db_session.commit()

    def modify_election(self, modified_info:dict) -> tuple[str,str] | None:
        """
        Update the election info using user input

        :param modified_info: dictionary of all the modified information
        :return: None
        """

        for key, value in modified_info.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                return f"{key} attribute not found in Election class", "danger"

    def election_info(self) -> dict:
        """ provide election details """
        info = {
            "creators_id": self.creators_id,
            "title": self.title,
            "explanation": self.explanation,
            "type_of_election": self.type_of_election,
            "key": self.key,
            "is_active": self.is_active,
            "start_of_candidate_selection": self.start_of_candidate_selection,
            "end_of_candidate_selection": self.end_of_candidate_selection,
            "start_of_election": self.start_of_election,
            "end_of_election": self.end_of_election,
            "candidates": self.candidates
        }
        return info

    def make_card(self) -> dict:
        """ Generates a summarized representation of an election. """
        card = {
            "id" : self.id,
            "creators_id" : self.creators_id,
            "title" : self.title,
            "explanation" : self.explanation,
            "type_of_election" : self.type_of_election,
            "key" : self.key,
            "is_active" : self.is_active,
            "visibility" : self.visibility,
            "start_of_candidate_selection" : self.start_of_candidate_selection,
            "end_of_candidate_selection" : self.end_of_candidate_selection ,
            "start_of_election" : self.start_of_election,
            "end_of_election" : self.end_of_election
        }

        return card

    @classmethod
    def check_key(cls, key) -> bool:
        return cls.query.filter_by(key=key).one_or_none() is None

    @classmethod
    def random_election(cls, no_of_elections) -> Info:
        """
        Retrieves a random selection of public, active elections.
        :param no_of_elections: integer
        :return: Info
        """

        e_list = []
        elections = cls.query.filter_by(visibility="public", is_active=True).order_by(func.random()).limit(no_of_elections).all()

        if not elections:
            return e_list

        rand_elections = random.sample(elections, min(no_of_elections, len(elections)))

        for election in rand_elections:
            e_list.append(election.make_card())

        return e_list

    @classmethod
    def public_search(cls, search) -> Info:
        e_list = []
        search = f"%{search}%"

        query = cls.query.where(
            and_(
                or_(
                    cls.title.like(search),
                    cls.explanation.like(search),
                    cls.type_of_election.like(search),
                    cls.key.like(search)
                ),
                cls.visibility == "public"
            )
        ).all()

        for election in query:
            e_list.append(election.make_card())

        return e_list

    @classmethod
    def private_search(cls, search: str) -> Info | None:
        e_list = []
        query = cls.query.filter_by(key = search, visibility="private").one_or_none()

        if not query:
            return None

        for election in query:
            e_list.append(election.make_card())

        return e_list
