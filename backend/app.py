from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from datetime import timedelta
import bcrypt
from config import Config
from database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
CORS(app, origins=Config.CORS_ORIGINS)
JWTManager(app)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    storage_uri=Config.RATELIMIT_STORAGE_URL,
    default_limits=[Config.RATELIMIT_DEFAULT]
)

# Initialize database
db = Database()

# Simple authentication (in production, use proper user management)
USERS = {
    'admin': bcrypt.hashpw('athletics2024'.encode('utf-8'), bcrypt.gensalt())
}

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """Authenticate user and return JWT token"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        if username in USERS and bcrypt.checkpw(password.encode('utf-8'), USERS[username]):
            access_token = create_access_token(
                identity=username,
                expires_delta=timedelta(hours=24)
            )
            return jsonify({
                'access_token': access_token,
                'user': username
            })
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        logging.error(f"Login error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

@app.route('/api/competitions', methods=['GET'])
@jwt_required()
@limiter.limit("100 per hour")
def get_competitions():
    """Get competitions with optional search and pagination"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        search = request.args.get('search')
        
        offset = (page - 1) * per_page
        
        competitions = db.get_competitions(
            limit=per_page,
            offset=offset,
            search=search
        )
        
        if competitions is None:
            return jsonify({'error': 'Failed to fetch competitions'}), 500
        
        return jsonify({
            'competitions': competitions,
            'page': page,
            'per_page': per_page,
            'total': len(competitions)
        })
        
    except Exception as e:
        logging.error(f"Error fetching competitions: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/athletes', methods=['GET'])
@jwt_required()
@limiter.limit("100 per hour")
def get_athletes():
    """Get athletes with optional search and pagination"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        search = request.args.get('search')
        
        offset = (page - 1) * per_page
        
        athletes = db.get_athletes(
            limit=per_page,
            offset=offset,
            search=search
        )
        
        if athletes is None:
            return jsonify({'error': 'Failed to fetch athletes'}), 500
        
        return jsonify({
            'athletes': athletes,
            'page': page,
            'per_page': per_page,
            'total': len(athletes)
        })
        
    except Exception as e:
        logging.error(f"Error fetching athletes: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/competitions/<int:competition_id>/results', methods=['GET'])
@jwt_required()
@limiter.limit("100 per hour")
def get_competition_results(competition_id):
    """Get results for a specific competition"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))
        
        offset = (page - 1) * per_page
        
        results = db.get_results_by_competition(
            competition_id=competition_id,
            limit=per_page,
            offset=offset
        )
        
        if results is None:
            return jsonify({'error': 'Failed to fetch results'}), 500
        
        return jsonify({
            'results': results,
            'competition_id': competition_id,
            'page': page,
            'per_page': per_page,
            'total': len(results)
        })
        
    except Exception as e:
        logging.error(f"Error fetching competition results: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/athletes/<int:athlete_id>/results', methods=['GET'])
@jwt_required()
@limiter.limit("100 per hour")
def get_athlete_results(athlete_id):
    """Get results for a specific athlete"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        offset = (page - 1) * per_page
        
        results = db.get_results_by_athlete(
            athlete_id=athlete_id,
            limit=per_page,
            offset=offset
        )
        
        if results is None:
            return jsonify({'error': 'Failed to fetch results'}), 500
        
        return jsonify({
            'results': results,
            'athlete_id': athlete_id,
            'page': page,
            'per_page': per_page,
            'total': len(results)
        })
        
    except Exception as e:
        logging.error(f"Error fetching athlete results: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/disciplines', methods=['GET'])
@jwt_required()
@limiter.limit("100 per hour")
def get_disciplines():
    """Get all disciplines"""
    try:
        disciplines = db.get_disciplines()
        
        if disciplines is None:
            return jsonify({'error': 'Failed to fetch disciplines'}), 500
        
        return jsonify({'disciplines': disciplines})
        
    except Exception as e:
        logging.error(f"Error fetching disciplines: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/countries', methods=['GET'])
@jwt_required()
@limiter.limit("100 per hour")
def get_countries():
    """Get all countries"""
    try:
        countries = db.get_countries()
        
        if countries is None:
            return jsonify({'error': 'Failed to fetch countries'}), 500
        
        return jsonify({'countries': countries})
        
    except Exception as e:
        logging.error(f"Error fetching countries: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/stats', methods=['GET'])
@jwt_required()
@limiter.limit("50 per hour")
def get_stats():
    """Get database statistics"""
    try:
        # Get counts for different entities
        competitions_count = db.execute_query("SELECT COUNT(*) as count FROM competitions")[0]['count']
        athletes_count = db.execute_query("SELECT COUNT(*) as count FROM athletes")[0]['count']
        results_count = db.execute_query("SELECT COUNT(*) as count FROM results")[0]['count']
        events_count = db.execute_query("SELECT COUNT(*) as count FROM events")[0]['count']
        
        return jsonify({
            'competitions': competitions_count,
            'athletes': athletes_count,
            'results': results_count,
            'events': events_count
        })
        
    except Exception as e:
        logging.error(f"Error fetching stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        if db.connect():
            db.disconnect()
            return jsonify({'status': 'healthy', 'database': 'connected'})
        else:
            return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 500
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Test database connection on startup
    if db.connect():
        logging.info("Database connection successful")
        db.disconnect()
    else:
        logging.error("Failed to connect to database")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
