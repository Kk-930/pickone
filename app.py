from flask import Flask, render_template, redirect, url_for, session, flash, request
import os
import secrets # Used for a secure session key

# Initialize the Flask app
app = Flask(__name__)

# Set a secure secret key for session management (CRITICAL for security)
# This key is used to sign the session cookie.
# In a real app, use an environment variable (os.environ.get('SECRET_KEY'))
app.config['SECRET_KEY'] = secrets.token_hex(16) 

# --- Game Configuration ---
# Your secret options list. The numbers correspond to the index + 1
OPTIONS = [
    "A Surprise Weekend Getaway!", 
    "A New Gadget You've Been Eyeing!", 
    "A Home-Cooked Meal of Your Choice and a Movie Night!",
    "A Free Pass on One Chore for a Month!"
]
# ---------------------------

@app.route('/', methods=['GET', 'POST'])
def index():
    # 'chosen_option' is stored in the user's session once they make a choice
    chosen_option_index = session.get('chosen_option', -1)
    
    # If a choice has already been made, just show the result page
    if chosen_option_index != -1:
        chosen_option_text = OPTIONS[chosen_option_index]
        return render_template('index.html', 
                               options_count=len(OPTIONS),
                               chosen_option=chosen_option_text,
                               game_over=True)

    # Handle the form submission (when the user taps a number)
    if request.method == 'POST':
        try:
            # Get the chosen number and convert it to a list index
            choice = int(request.form.get('choice'))
            chosen_index = choice - 1
            
            # 1. Check if the choice is valid
            if 0 <= chosen_index < len(OPTIONS):
                # 2. Store the choice in the session and redirect
                session['chosen_option'] = chosen_index
                flash(f"You picked number {choice}!") # Flash a quick message (optional)
                return redirect(url_for('index')) # Redirect to GET to show the result
            else:
                return "Invalid option selected", 400
        except:
            return "Error processing choice", 500

    # For the initial GET request (or after a failed POST)
    # Renders the numbered list for the partner to choose from
    return render_template('index.html', 
                           options_count=len(OPTIONS), 
                           game_over=False)

if __name__ == '__main__':
    # Start the web server
    app.run(debug=True)