from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import os
import logging
from ecommbot.bot import EcommChatBot

load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize the chat bot
bot = EcommChatBot()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_input = data.get("message")
        session_id = data.get("session_id", "default_session")
        
        if not user_input:
            return jsonify({"error": "Message is required"}), 400
            
        result = bot.ask(user_input, session_id=session_id)
        logger.info(f"Response generated for session '{session_id}'")
        
        return jsonify({"response": result})
    except Exception as e:
        logger.error("Error in /chat endpoint", exc_info=True)
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

if __name__ == '__main__':
    # Determine environment, default securely to production
    env = os.getenv("ENVIRONMENT", "production").lower()
    
    if env == "development":
        print("Starting server in DEVELOPMENT mode with debug enabled.")
        app.run(debug=True, host="0.0.0.0", port=5000)
    else:
        print("Starting server in PRODUCTION mode.")
        print("WARNING: Using Flask's built-in server in production is not recommended.")
        print("Consider executing via a WSGI server like 'waitress-serve' or 'gunicorn'.")
        # Run with debug disabled in production, binding to 0.0.0.0
        app.run(debug=False, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))