from flask import Flask, render_template, redirect, url_for, session, request
from flask_sqlalchemy import SQLAlchemy
import secrets
import os
import json # Used to store prize list as a JSON string

# --- Configuration ---
app = Flask(__name__)

# Use an environment variable for the Secret Key (CRITICAL for deployment)
# If running locally, it defaults to a secure random key.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Database Configuration (SQLite for simplicity)
# When deployed on Render's free tier, you'd use a managed database like Postgres.
# For a simple game like this, SQLite is okay for small-scale use.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///games.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Model ---
class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    # The prize options are stored as a JSON string
    options_json = db.Column(db.Text, nullable=False)
    # The winning choice is stored here (index, not number)
    chosen_index = db.Column(db.Integer, default=-1) # -1 means no choice yet

    def get_options(self):
        return json.loads(self.options_json)

# Initialize the database and create tables
with app.app_context():
    db.create_all()

# --- Routes ---

# 1. Homepage (Start/Instructions)
@app.route('/')
def index():
    return render_template('index.html')

# 2. Game Creation Form
@app.route('/create', methods=['GET', 'POST'])
def create_game():
    if request.method == 'POST':
        game_title = request.form.get('title')
        # Get all options from the form (up to 4 in this example)
        options = []
        for i in range(1, 5):
            option = request.form.get(f'option_{i}', '').strip()
            if option:
                options.append(option)
        
        if not game_title or len(options) < 2:
            # Simple error handling
            return "Error: Game needs a title and at least two options.", 400

        # Create a new Game object and save to database
        new_game = Game(
            title=game_title,
            options_json=json.dumps(options)
        )
        db.session.add(new_game)
        db.session.commit()

        # Redirect to the unique game page
        return redirect(url_for('game_page', game_id=new_game.id))

    # For GET request, show the creation form
    return render_template('create.html')

# 3. The Sharable Game Page
@app.route('/game/<int:game_id>', methods=['GET', 'POST'])
def game_page(game_id):
    game = db.session.get(Game, game_id)
    if not game:
        return "Game not found.", 404
        
    options = game.get_options()
    
    # Handle the choice submission
    if request.method == 'POST':
        # Check if a choice has already been made
        if game.chosen_index != -1:
            # Prevent re-submitting if the game is already over
            return redirect(url_for('game_page', game_id=game_id))
            
        try:
            # Get the chosen number (1-based index)
            choice = int(request.form.get('choice'))
            chosen_index = choice - 1
            
            # 1. Validate the choice
            if 0 <= chosen_index < len(options):
                # 2. Record the choice in the database
                game.chosen_index = chosen_index
                db.session.commit()
                # Redirect to GET to show the result
                return redirect(url_for('game_page', game_id=game_id))
            else:
                return "Invalid option selected", 400
        except:
            return "Error processing choice", 500

    # For GET request, render the game page
    game_over = game.chosen_index != -1
    chosen_option_text = options[game.chosen_index] if game_over else None
    share_link = request.url # The current URL is the share link

    return render_template('game.html', 
                           game=game,
                           options_count=len(options),
                           chosen_option=chosen_option_text,
                           game_over=game_over,
                           share_link=share_link)

if __name__ == '__main__':
    app.run(debug=True)