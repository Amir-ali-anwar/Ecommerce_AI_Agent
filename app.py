from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import os
from ecommbot.bot import EcommChatBot

load_dotenv()

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
        print("Response : ", result)
        
        return jsonify({"response": result})
    except Exception as e:
        import traceback
        print(f"Error in /chat: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)