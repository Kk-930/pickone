from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
import secrets
import os
import json
import smtplib
from email.message import EmailMessage

# --- Configuration ---
app = Flask(__name__)

# Use an environment variable for the Secret Key (CRITICAL for deployment)
# This is used by Flask for session management.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Database Configuration: Use a SQLite file named games.db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///games.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Model ---
class Game(db.Model):
    """
    Represents a single pick-a-prize game instance.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    # NEW: Store the creator's email for notification
    creator_email = db.Column(db.String(100), nullable=True) 
    # JSON string storing the list of prize options
    options_json = db.Column(db.Text, nullable=False)
    # Index of the chosen option (-1 means no choice has been made yet)
    chosen_index = db.Column(db.Integer, default=-1) 

    def get_options(self):
        """Helper to deserialize the options from the database."""
        return json.loads(self.options_json)

# Create the database tables before the first request
@app.before_request
def create_tables():
    db.create_all()

# --- Email Functionality ---
# NOTE: These must be set as environment variables (SMTP_SERVER, SMTP_PORT, etc.) 
# in your Render dashboard for email sending to work!
SMTP_SERVER = os.environ.get('SMTP_SERVER')
SMTP_PORT = os.environ.get('SMTP_PORT')
SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')

def send_notification_email(recipient_email, game_title, selected_prize, game_url):
    """Sends an email notification to the creator when a choice is made."""
    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD]):
        print("EMAIL CONFIGURATION MISSING. Notification not sent.")
        return

    try:
        msg = EmailMessage()
        msg['Subject'] = f"🎁 Game Reveal: '{game_title}' Has Been Picked!"
        msg['From'] = SMTP_USERNAME
        msg['To'] = recipient_email

        # The body contains the crucial piece of information: the chosen prize
        body = f"""
        Hello!

        Your game, '{game_title}', has been played and the prize has been revealed!

        The recipient chose: "{selected_prize}"

        This confirms the true selection, so you know the result!

        You can view the final, permanent result here:
        {game_url}

        Happy Gifting!
        """
        msg.set_content(body)

        # Connect to the SMTP server and send the email
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()  # Use TLS encryption for security
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            print(f"Successfully sent notification to {recipient_email}")

    except Exception as e:
        print(f"Error sending email: {e}")

# --- Routes ---

@app.route('/')
def index():
    """Main landing page."""
    return render_template('index.html')

@app.route('/create', methods=['GET', 'POST'])
def create_game():
    """Handles the creation form and saves the new game to the database."""
    if request.method == 'POST':
        game_title = request.form.get('title')
        creator_email = request.form.get('creator_email') # NEW: Collect creator's email
        
        # Collect and filter options
        options = []
        for i in range(1, 5):
            option = request.form.get(f'option_{i}', '').strip()
            if option:
                options.append(option)
        
        # Basic validation
        if not game_title or not creator_email or len(options) < 2:
            return "Error: Game needs a title, your email, and at least two options.", 400

        # Create a new Game object and save to database
        new_game = Game(
            title=game_title,
            creator_email=creator_email, # Save the creator's email
            options_json=json.dumps(options)
        )
        db.session.add(new_game)
        db.session.commit()
        
        # Redirect to the unique game page
        return redirect(url_for('game_page', game_id=new_game.id))

    return render_template('create.html')

@app.route('/game/<int:game_id>', methods=['GET', 'POST'])
def game_page(game_id):
    """Displays the game and handles the choice submission."""
    game = Game.query.get_or_404(game_id)
    options = game.get_options()
    
    # Handle the choice submission
    if request.method == 'POST':
        # Prevent double submission
        if game.chosen_index != -1:
            # If a choice was already made, just redirect to GET to show result
            return redirect(url_for('game_page', game_id=game_id))

        try:
            # Get the index (0-based) of the chosen option from the form
            chosen_index = int(request.form.get('chosen_index'))
        except (TypeError, ValueError):
            return "Invalid choice submitted.", 400
        
        # 1. Validate the choice index
        if 0 <= chosen_index < len(options):
            # 2. Record the choice in the database
            game.chosen_index = chosen_index
            db.session.commit()
            
            # --- CRITICAL: SEND NOTIFICATION EMAIL HERE ---
            # Get the actual prize text for the email
            selected_prize = options[chosen_index]
            game_url = request.url_root.rstrip('/') + url_for('game_page', game_id=game_id)
            
            # Send notification to the creator's email
            send_notification_email(
                game.creator_email, 
                game.title, 
                selected_prize, 
                game_url
            )
            # ---------------------------------------------
            
            # Redirect to GET to show the result
            return redirect(url_for('game_page', game_id=game_id))
        else:
            return "Invalid choice index.", 400
            
    # GET request: Display the game page
    return render_template(
        'game.html', 
        game=game, 
        options=options, 
        chosen_index=game.chosen_index
    )

@app.route('/list')
def list_games():
    """Lists all created games (for debugging/admin purposes)."""
    games = Game.query.all()
    return render_template('list_games.html', games=games)

if __name__ == '__main__':
    # When running locally, ensure the DB is initialized
    with app.app_context():
        db.create_all()
    # Run the application
    app.run(debug=True)
