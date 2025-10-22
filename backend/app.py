"""
Flask backend for the TON Trivia Battle mini app.

This server hosts the static frontend files and exposes simple JSON
endpoints for retrieving trivia questions and recording match results.
You can run this locally for testing or deploy it to a cloud service.

Run with:

    pip install flask
    python app.py

Then visit http://localhost:8000 in your browser. When deploying, be sure
to configure HTTPS and update the `frontend/tonconnect-manifest.json` and
`frontend/index.html` files with your real domain.
"""

from flask import Flask, jsonify, request, send_from_directory
import os
import random
import json


# Path to the directory containing the frontend files. We use an
# absolute path so the server can locate the files regardless of
# where it is started from.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')

# Commission configuration. When a player wins a game, a percentage of
# the stake will be sent to the owner's wallet. Adjust the rate and
# owner wallet address as needed for your deployment.
COMMISSION_RATE = 0.15  # 15% commission
# Default owner wallet address for commission settlement. This value can be
# overridden at runtime by setting the OWNER_WALLET environment variable.
OWNER_WALLET = os.environ.get("OWNER_WALLET", "UQC6JjZfg6wpyIq7EoiFyFelqH9GvnMABdV9CasyAzJWX9Xa")

# Path to a JSON file where cumulative scores are stored. The file lives
# alongside the backend folder. When results are posted, the scores
# are read, updated and written back so that a leaderboard can be
# served. This provides a simple persistence mechanism. In a real
# application you would likely use a proper database.
SCORES_FILE = os.path.join(BASE_DIR, 'scores.json')


def load_scores() -> dict:
    """Load the persistent scores from the JSON file.

    Returns a dictionary mapping a player's identifier to their total
    score. If the file does not exist or is unreadable, an empty
    dictionary is returned.
    """
    try:
        with open(SCORES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_scores(scores: dict) -> None:
    """Persist the scores dictionary to the JSON file."""
    with open(SCORES_FILE, 'w', encoding='utf-8') as f:
        json.dump(scores, f)

# Categorised trivia questions. In a production version you could
# dynamically fetch questions using an external API such as OpenAI's
# ChatGPT API. For demonstration purposes we use a static set of
# English questions per category. Feel free to extend these lists.
CATEGORIES = {
    "general": [
        {
            "question": "What is the capital city of France?",
            "options": ["Berlin", "Madrid", "Paris", "Rome"],
            "correctIndex": 2,
        },
        {
            "question": "Which planet is known as the Red Planet?",
            "options": ["Earth", "Mars", "Venus", "Jupiter"],
            "correctIndex": 1,
        },
        {
            "question": "Who wrote the play 'Romeo and Juliet'?",
            "options": ["William Shakespeare", "Jane Austen", "Mark Twain", "Charles Dickens"],
            "correctIndex": 0,
        },
        {
            "question": "How many continents are there on Earth?",
            "options": ["Five", "Six", "Seven", "Eight"],
            "correctIndex": 2,
        },
        {
            "question": "What gas do plants absorb from the atmosphere?",
            "options": ["Oxygen", "Nitrogen", "Carbon Dioxide", "Hydrogen"],
            "correctIndex": 2,
        },
    ],
    "football": [
        {
            "question": "Which country won the FIFA World Cup in 2018?",
            "options": ["Brazil", "France", "Germany", "Argentina"],
            "correctIndex": 1,
        },
        {
            "question": "Who is known as 'El Pibe de Oro' in football?",
            "options": ["Lionel Messi", "Diego Maradona", "Cristiano Ronaldo", "Pelé"],
            "correctIndex": 1,
        },
        {
            "question": "Which club does Mohamed Salah play for (as of 2024)?",
            "options": ["Liverpool", "Real Madrid", "Chelsea", "Paris Saint-Germain"],
            "correctIndex": 0,
        },
        {
            "question": "How long is a standard football match (excluding injury time)?",
            "options": ["80 minutes", "90 minutes", "100 minutes", "120 minutes"],
            "correctIndex": 1,
        },
        {
            "question": "Which country has won the most UEFA Champions League titles?",
            "options": ["England", "Spain", "Italy", "Germany"],
            "correctIndex": 1,
        },
    ],
    "crypto": [
        {
            "question": "What was the first cryptocurrency ever created?",
            "options": ["Ethereum", "Litecoin", "Bitcoin", "Dogecoin"],
            "correctIndex": 2,
        },
        {
            "question": "Who is credited as the creator of Bitcoin?",
            "options": ["Vitalik Buterin", "Satoshi Nakamoto", "Charlie Lee", "Jed McCaleb"],
            "correctIndex": 1,
        },
        {
            "question": "Which blockchain platform introduced smart contracts?",
            "options": ["Bitcoin", "Ripple", "Ethereum", "Cardano"],
            "correctIndex": 2,
        },
        {
            "question": "What does NFT stand for?",
            "options": ["New Finance Token", "Non-Fungible Token", "Network Fee Transaction", "Non-Financial Transaction"],
            "correctIndex": 1,
        },
        {
            "question": "Which consensus algorithm does Bitcoin use?",
            "options": ["Proof of Stake", "Proof of Authority", "Proof of Work", "Delegated Proof of Stake"],
            "correctIndex": 2,
        },
    ],
}


@app.route('/')
def serve_index():
    """Serve the main HTML page."""
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/questions')
def get_questions():
    """
    Return a random selection of up to five questions for a given
    category. Clients can specify a category via the "category"
    query parameter. If no category is provided or an unknown
    category is requested, questions from the "general" category
    will be returned.
    """
    category = request.args.get('category', 'general').lower()
    questions_pool = CATEGORIES.get(category, CATEGORIES['general'])
    n = min(5, len(questions_pool))
    selected = random.sample(questions_pool, n)
    return jsonify({'questions': selected})


@app.route('/result', methods=['POST'])
def receive_result():
    """
    Handle match results posted by the client. The request body should
    contain:

        {
            "wallet": { ... },  # Telegram wallet or TonConnect info
            "score": {"user": int, "opponent": int},
            "stake": float (optional, defaults to 1.0),
            "category": str (optional, for analytics)
        }

    The winner is determined by comparing the user and opponent scores.
    A commission is calculated from the stake and logged. In a
    production environment you would validate the init data and perform
    an on-chain settlement using the Ton blockchain. Here we simply
    compute and return the settlement breakdown.
    """
    data = request.get_json(silent=True) or {}
    wallet = data.get('wallet')
    score = data.get('score', {})
    user_score = int(score.get('user', 0))
    opp_score = int(score.get('opponent', 0))
    stake = float(data.get('stake', 1.0))
    category = data.get('category', 'general')

    # Determine winner and calculate commission
    if user_score > opp_score:
        winner = 'user'
    elif user_score < opp_score:
        winner = 'opponent'
    else:
        winner = 'tie'

    # Commission applies only if there is a winner
    commission = 0.0
    net_reward = 0.0
    if winner != 'tie':
        commission = stake * COMMISSION_RATE
        net_reward = stake - commission

    # Log the settlement details. Replace this with actual TON
    # transaction logic using the winner's wallet address.
    print(f"Received result from wallet {wallet} for category {category}.")
    print(f"Score - user: {user_score}, opponent: {opp_score}; winner: {winner}")
    print(f"Stake: {stake} TON, commission: {commission} TON, net reward: {net_reward} TON")
    if commission:
        print(f"Commission of {commission} TON should be sent to owner wallet {OWNER_WALLET}.")

    # Update persistent leaderboard. We attempt to identify the player
    # from the provided wallet information. The wallet structure
    # supplied by TonConnect may vary; for robustness we convert the
    # entire wallet object to a string if a specific address field is
    # not found.
    player_id = None
    try:
        # Wallet may be a dictionary with account info. Try common keys.
        if isinstance(wallet, dict):
            # TonConnect passes account info under "account" or directly as "address".
            if 'account' in wallet and isinstance(wallet['account'], dict):
                player_id = wallet['account'].get('address')
            if not player_id:
                player_id = wallet.get('address') or wallet.get('publicKey')
        # Fallback to string representation
        if not player_id:
            player_id = str(wallet)
    except Exception:
        player_id = str(wallet)

    # Update the scoreboard with the player's score. For simplicity
    # we add the number of correct answers the player achieved in this
    # match to their cumulative score. In a full implementation you
    # might track wins or other metrics instead.
    try:
        scores = load_scores()
        # Ensure the ID is a string for JSON compatibility.
        if player_id not in scores:
            scores[player_id] = 0
        scores[player_id] += user_score
        save_scores(scores)
    except Exception as e:
        print(f"Failed to update leaderboard: {e}")

    return jsonify({
        'status': 'ok',
        'winner': winner,
        'commission': commission,
        'net_reward': net_reward
    })


@app.route('/leaderboard')
def get_leaderboard():
    """Return the leaderboard sorted by total score.

    Each entry includes a player identifier, their cumulative score and
    their rank in the leaderboard. The rank is 1-based.
    """
    scores = load_scores()
    # Sort players by score descending, then by identifier for stability
    sorted_scores = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    leaderboard_list = []
    rank = 1
    for player, pts in sorted_scores:
        leaderboard_list.append({'player': player, 'score': pts, 'rank': rank})
        rank += 1
    return jsonify({'leaderboard': leaderboard_list})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    # Listen on all interfaces so it can be accessed externally if needed.
    app.run(host='0.0.0.0', port=port)
