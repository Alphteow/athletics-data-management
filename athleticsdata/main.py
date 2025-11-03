from firebase_functions import https_fn
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import os
import psycopg
from psycopg.rows import dict_row
from firebase_admin import initialize_app, auth as firebase_auth
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
# In production (Cloud Run), these should be set via environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Initialize Firebase Admin
# For Cloud Run, use default credentials
# For local development, set GOOGLE_APPLICATION_CREDENTIALS env var
try:
    # Initialize with project ID from environment or default
    from firebase_admin import credentials
    import firebase_admin
    
    # Check if already initialized
    if not firebase_admin._apps:
        # Use application default credentials (works in Cloud Run)
        cred = credentials.ApplicationDefault()
        initialize_app(cred, {
            'projectId': os.getenv('FIREBASE_PROJECT_ID', 'athletics-data-8fb35'),
        })
        logging.info("Firebase Admin initialized successfully")
    else:
        logging.info("Firebase Admin already initialized")
except Exception as e:
    logging.error(f"Failed to initialize Firebase Admin: {e}")
    logging.error("Continuing without Firebase Admin - auth will fail")
    # Continue anyway - we'll handle auth errors per-request

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Initialize extensions
CORS(app, origins=[
    "https://athletics-data-8fb35.web.app", 
    "https://athletics-data-8fb35.firebaseapp.com", 
    "http://localhost:3001",
    "https://athletics-data-8fb35.firebaseapp.com"
])
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["100 per hour"]
)
limiter.init_app(app)

# Database configuration
class Database:
    def __init__(self):
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """Establish secure database connection with SSL/TLS"""
        try:
            # Require all credentials from environment variables (no defaults for sensitive data)
            db_host = os.getenv('DB_HOST')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME')
            db_user = os.getenv('DB_USER')
            db_password = os.getenv('DB_PASSWORD')
            
            # Validate required credentials
            if not all([db_host, db_name, db_user, db_password]):
                missing = []
                if not db_host: missing.append('DB_HOST')
                if not db_name: missing.append('DB_NAME')
                if not db_user: missing.append('DB_USER')
                if not db_password: missing.append('DB_PASSWORD')
                raise ValueError(f"Missing required database environment variables: {', '.join(missing)}")
            
            # Connect with SSL/TLS encryption required
            self.connection = psycopg.connect(
                host=db_host,
                port=int(db_port),
                dbname=db_name,
                user=db_user,
                password=db_password,
                sslmode='require',  # Force SSL/TLS encryption
                row_factory=dict_row
            )
            self.cursor = self.connection.cursor()
            logging.info("Secure database connection established successfully")
            return True
        except Exception as e:
            logging.error(f"Database connection failed: {e}")
            # Don't log sensitive information
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logging.info("Database connection closed")
    
    def execute_query(self, query, params=None):
        """Execute a SELECT query and return results with parameterized queries for security"""
        cursor = None
        try:
            # Check if connection exists and is valid
            if not self.connection or self.connection.closed:
                if not self.connect():
                    return None
            
            # Create a new cursor for each query
            cursor = self.connection.cursor(row_factory=dict_row)
            # Use parameterized queries to prevent SQL injection
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except psycopg.OperationalError as e:
            # Connection error - try to reconnect once
            logging.warning(f"Connection error, attempting reconnect: {e}")
            if self.connection:
                try:
                    self.disconnect()
                except:
                    pass
            if self.connect():
                try:
                    cursor = self.connection.cursor(row_factory=dict_row)
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
                except Exception as retry_error:
                    logging.error(f"Query execution failed after reconnect: {retry_error}")
                    return None
            return None
        except Exception as e:
            logging.error(f"Query execution failed: {e}")
            # Don't log query parameters or sensitive data
            return None
        finally:
            # Always close the cursor to free resources
            if cursor:
                cursor.close()
    
    def get_competitions(self, limit=50, offset=0, search=None):
        """Get competitions with optional search - only those that have results"""
        query = """
        SELECT DISTINCT c.*, co.name as country_name, rc.name as ranking_category_name,
               COUNT(r.id) as result_count
        FROM competitions c
        LEFT JOIN countries co ON c.country_code = co.code
        LEFT JOIN ranking_categories rc ON c.ranking_category_id = rc.id
        LEFT JOIN races ra ON c.id = ra.competition_id
        LEFT JOIN results r ON ra.id = r.race_id AND r.mark IS NOT NULL AND r.mark != ''
        """
        
        params = []
        if search:
            query += " WHERE (c.name ILIKE %s OR c.venue ILIKE %s OR co.name ILIKE %s)"
            params = [f"%{search}%", f"%{search}%", f"%{search}%"]
        
        query += " GROUP BY c.id, co.name, rc.name"
        query += " HAVING COUNT(r.id) > 0"  # Only competitions with results
        query += " ORDER BY result_count DESC, c.start_date DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        return self.execute_query(query, params)
    
    def get_competitions_count(self, search=None):
        """Get total count of competitions with results matching search criteria"""
        query = """
        SELECT COUNT(DISTINCT c.id) as count
        FROM competitions c
        LEFT JOIN countries co ON c.country_code = co.code
        LEFT JOIN races ra ON c.id = ra.competition_id
        LEFT JOIN results r ON ra.id = r.race_id AND r.mark IS NOT NULL AND r.mark != ''
        """
        
        params = []
        if search and len(search.strip()) >= 2:
            query += " WHERE (c.name ILIKE %s OR c.venue ILIKE %s OR co.name ILIKE %s)"
            search_term = f"%{search.strip()}%"
            params = [search_term, search_term, search_term]
        
        query += " HAVING COUNT(r.id) > 0"
        
        result = self.execute_query(query, params)
        return result[0]['count'] if result else 0
    
    def get_athletes(self, limit=50, offset=0, search=None, sort_by='full_name', sort_order='ASC'):
        """Get athletes with optional search and sorting"""
        # Validate sort parameters to prevent SQL injection
        valid_sort_fields = ['full_name', 'family_name', 'given_name', 'country_code', 'birth_date']
        valid_sort_orders = ['ASC', 'DESC']
        
        sort_by = sort_by if sort_by in valid_sort_fields else 'full_name'
        sort_order = sort_order if sort_order in valid_sort_orders else 'ASC'
        
        query = """
        SELECT a.*, co.name as country_name
        FROM athletes a
        LEFT JOIN countries co ON a.country_code = co.code
        """
        
        params = []
        if search and len(search.strip()) >= 2:  # Minimum 2 characters for search
            # Prioritize name matches over country matches
            # Only search country if it looks like a country code (2-3 uppercase letters)
            search_clean = search.strip()
            is_country_code = len(search_clean) <= 3 and search_clean.isupper()
            
            if is_country_code:
                # If it looks like a country code, search both names and country
                query += """ WHERE (
                    a.full_name ILIKE %s OR 
                    a.family_name ILIKE %s OR 
                    a.given_name ILIKE %s OR 
                    a.country_code ILIKE %s OR
                    co.name ILIKE %s
                )"""
                search_term = f"%{search_clean}%"
                params = [search_term, search_term, search_term, search_term, search_term]
            else:
                # Otherwise, only search names (not country)
                query += """ WHERE (
                    a.full_name ILIKE %s OR 
                    a.family_name ILIKE %s OR 
                    a.given_name ILIKE %s
                )"""
                search_term = f"%{search_clean}%"
                params = [search_term, search_term, search_term]
        
        query += f" ORDER BY a.{sort_by} {sort_order} LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        return self.execute_query(query, params)
    
    def get_athletes_count(self, search=None):
        """Get total count of athletes matching search criteria"""
        query = """
        SELECT COUNT(*) as count
        FROM athletes a
        LEFT JOIN countries co ON a.country_code = co.code
        """
        
        params = []
        if search and len(search.strip()) >= 2:
            # Prioritize name matches over country matches
            # Only search country if it looks like a country code (2-3 uppercase letters)
            search_clean = search.strip()
            is_country_code = len(search_clean) <= 3 and search_clean.isupper()
            
            if is_country_code:
                # If it looks like a country code, search both names and country
                query += """ WHERE (
                    a.full_name ILIKE %s OR 
                    a.family_name ILIKE %s OR 
                    a.given_name ILIKE %s OR 
                    a.country_code ILIKE %s OR
                    co.name ILIKE %s
                )"""
                search_term = f"%{search_clean}%"
                params = [search_term, search_term, search_term, search_term, search_term]
            else:
                # Otherwise, only search names (not country)
                query += """ WHERE (
                    a.full_name ILIKE %s OR 
                    a.family_name ILIKE %s OR 
                    a.given_name ILIKE %s
                )"""
                search_term = f"%{search_clean}%"
                params = [search_term, search_term, search_term]
        
        result = self.execute_query(query, params)
        return result[0]['count'] if result else 0
    
    def get_results_by_competition(self, competition_id, limit=100, offset=0):
        """Get results for a specific competition - optimized"""
        query = """
        SELECT r.*, 
               COALESCE(a.full_name, r.athlete_name) as athlete_name, 
               COALESCE(a.country_code, r.nationality) as athlete_country,
               c.start_date as race_date, 
               COALESCE(ra.race_type, 'Final') as race_type, 
               e.event_name, e.discipline_code,
               COALESCE(d.discipline_name, e.event_name) as discipline_name,
               COALESCE(d.category, 'Track & Field') as category
        FROM results r
        JOIN races ra ON r.race_id = ra.id
        JOIN events e ON ra.event_id = e.id
        LEFT JOIN athletes a ON a.id = r.athlete_id
        JOIN competitions c ON ra.competition_id = c.id
        LEFT JOIN disciplines d ON e.discipline_code = d.discipline_code
        WHERE ra.competition_id = %s 
        AND r.mark IS NOT NULL 
        AND r.mark != ''
        ORDER BY c.start_date DESC, r.place ASC
        LIMIT %s OFFSET %s
        """
        
        return self.execute_query(query, [competition_id, limit, offset])
    
    def get_disciplines(self):
        """Get all disciplines"""
        query = "SELECT * FROM disciplines ORDER BY discipline_name"
        return self.execute_query(query)
    
    def get_countries(self):
        """Get all countries"""
        query = "SELECT * FROM countries ORDER BY name"
        return self.execute_query(query)

# Initialize database
db = Database()

def verify_firebase_token():
    """Verify Firebase ID token from Authorization header"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split('Bearer ')[1]
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logging.error(f"Token verification failed: {e}")
        return None

def firebase_auth_required(f):
    """Decorator to require Firebase authentication"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = verify_firebase_token()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        request.current_user = user
        return f(*args, **kwargs)

    return decorated_function

@app.route('/api/competitions', methods=['GET'])
@firebase_auth_required
@limiter.limit("100 per hour")
def get_competitions():
    """Get competitions with optional search and pagination - only those with results"""
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 200)  # Cap at 200 per page
        search = request.args.get('search')
        
        offset = (page - 1) * per_page
        
        # Get competitions and total count
        competitions = db.get_competitions(
            limit=per_page,
            offset=offset,
            search=search
        )
        
        total_count = db.get_competitions_count(search=search)
        
        if competitions is None:
            return jsonify({'error': 'Failed to fetch competitions'}), 500
        
        return jsonify({
            'competitions': competitions,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logging.error(f"Error fetching competitions: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/athletes', methods=['GET'])
@firebase_auth_required
@limiter.limit("200 per hour")
def get_athletes():
    """Get athletes with optional search, pagination, and sorting"""
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 200)  # Cap at 200 per page
        search = request.args.get('search')
        sort_by = request.args.get('sort_by', 'full_name')
        sort_order = request.args.get('sort_order', 'ASC')
        
        offset = (page - 1) * per_page
        
        # Get athletes and total count
        athletes = db.get_athletes(
            limit=per_page,
            offset=offset,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        total_count = db.get_athletes_count(search=search)
        
        if athletes is None:
            return jsonify({'error': 'Failed to fetch athletes'}), 500
        
        return jsonify({
            'athletes': athletes,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logging.error(f"Error fetching athletes: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/competitions/<int:competition_id>/results', methods=['GET'])
@firebase_auth_required
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
        
        # Get total count of results for this competition
        count_query = """
        SELECT COUNT(r.id) as count
        FROM results r
        JOIN races ra ON r.race_id = ra.id
        WHERE ra.competition_id = %s 
        AND r.mark IS NOT NULL 
        AND r.mark != ''
        """
        count_result = db.execute_query(count_query, [competition_id])
        total_count = count_result[0]['count'] if count_result else 0
        
        return jsonify({
            'results': results,
            'competition_id': competition_id,
            'page': page,
            'per_page': per_page,
            'total': total_count
        })
        
    except Exception as e:
        logging.error(f"Error fetching competition results: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/disciplines', methods=['GET'])
@firebase_auth_required
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
@firebase_auth_required
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

@app.route('/api/athletes/search', methods=['GET'])
@firebase_auth_required
@limiter.limit("300 per hour")
def search_athletes():
    """Quick search endpoint for athlete autocomplete"""
    try:
        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 10)), 50)  # Cap at 50 for autocomplete
        
        if len(query) < 2:
            return jsonify({'athletes': []})
        
        athletes = db.get_athletes(
            limit=limit,
            offset=0,
            search=query,
            sort_by='full_name',
            sort_order='ASC'
        )
        
        if athletes is None:
            return jsonify({'error': 'Failed to search athletes'}), 500
        
        # Return simplified data for autocomplete
        simplified_athletes = [
            {
                'id': athlete['id'],
                'full_name': athlete['full_name'],
                'country_name': athlete.get('country_name'),
                'country_code': athlete.get('country_code')
            }
            for athlete in athletes
        ]
        
        return jsonify({'athletes': simplified_athletes})
        
    except Exception as e:
        logging.error(f"Error searching athletes: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/competitions/<int:competition_id>/athletes', methods=['GET'])
@firebase_auth_required
@limiter.limit("100 per hour")
def get_competition_athletes(competition_id):
    """Get all athletes who participated in a specific competition"""
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 100)), 200)
        
        offset = (page - 1) * per_page
        
        # Optimized query - simpler grouping
        query = """
          SELECT 
              COALESCE(a.id, 0) as id,
              COALESCE(a.full_name, r.athlete_name) as full_name, 
              COALESCE(a.family_name, '') as family_name, 
              COALESCE(a.given_name, '') as given_name, 
              COALESCE(a.country_code, r.nationality) as country_code, 
              a.gender, 
              a.birth_date,
              co.name as country_name,
              COUNT(r.id) as result_count,
              MIN(r.place) as best_place,
              COUNT(DISTINCT e.event_name) as events_participated
          FROM results r
          JOIN races ra ON r.race_id = ra.id
          JOIN events e ON ra.event_id = e.id
          LEFT JOIN athletes a ON a.id = r.athlete_id
          LEFT JOIN countries co ON COALESCE(a.country_code, r.nationality) = co.code
          WHERE ra.competition_id = %s
          AND r.mark IS NOT NULL 
          AND r.mark != ''
          GROUP BY r.athlete_name, a.id, a.full_name, a.family_name, a.given_name, 
                   a.country_code, r.nationality, a.gender, a.birth_date, co.name
          ORDER BY result_count DESC
          LIMIT %s OFFSET %s
          """
        
        results = db.execute_query(query, [competition_id, per_page, offset])
        
        if results is None:
            return jsonify({'error': 'Failed to fetch competition athletes'}), 500
        
        # Get total count - simplified and fast
        count_query = """
          SELECT COUNT(DISTINCT r.athlete_name) as count
          FROM results r
          JOIN races ra ON r.race_id = ra.id
          WHERE ra.competition_id = %s
          AND r.mark IS NOT NULL 
          AND r.mark != ''
          """
        
        count_result = db.execute_query(count_query, [competition_id])
        total_count = count_result[0]['count'] if count_result else 0
        
        return jsonify({
            'athletes': results,
            'competition_id': competition_id,
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logging.error(f"Error fetching competition athletes: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/athletes/<int:athlete_id>/results', methods=['GET'])
@firebase_auth_required
@limiter.limit("100 per hour")
def get_athlete_results(athlete_id):
    """Get all results for a specific athlete by ID - also finds results by name match"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))
        
        offset = (page - 1) * per_page
        
        # First get the athlete's full name
        athlete_query = "SELECT full_name FROM athletes WHERE id = %s"
        athlete_data = db.execute_query(athlete_query, [athlete_id])
        
        if not athlete_data:
            return jsonify({'error': 'Athlete not found'}), 404
        
        athlete_full_name = athlete_data[0]['full_name']
        
        # Query results - prioritize athlete_id, fallback to athlete_name if no athlete_id
        query = """
          SELECT DISTINCT ON (r.id) r.*, 
                 COALESCE(a.full_name, r.athlete_name) as athlete_name, 
                 COALESCE(a.country_code, r.nationality) as athlete_country,
                 c.start_date as race_date, 
                 COALESCE(ra.race_type, 'Final') as race_type, 
                 e.event_name, e.discipline_code,
                 COALESCE(d.discipline_name, e.event_name) as discipline_name,
                 COALESCE(d.category, 'Track & Field') as category, 
                 c.name as competition_name, c.start_date
          FROM results r
          JOIN races ra ON r.race_id = ra.id
          JOIN events e ON ra.event_id = e.id
          LEFT JOIN athletes a ON a.id = r.athlete_id
          JOIN competitions c ON ra.competition_id = c.id
          LEFT JOIN disciplines d ON e.discipline_code = d.discipline_code
          WHERE (r.athlete_id = %s OR (r.athlete_id IS NULL AND r.athlete_name = %s))
          AND r.mark IS NOT NULL 
          AND r.mark != ''
          ORDER BY r.id, c.start_date DESC, r.place ASC
          LIMIT %s OFFSET %s
          """
        
        results = db.execute_query(query, [athlete_id, athlete_full_name, per_page, offset])
        
        if results is None:
            return jsonify({'error': 'Failed to fetch athlete results'}), 500
        
        # Get total count - simple and fast
        count_query = """
        SELECT COUNT(DISTINCT id) as count
        FROM results
        WHERE (athlete_id = %s OR (athlete_id IS NULL AND athlete_name = %s))
        AND mark IS NOT NULL 
        AND mark != ''
        """
        count_result = db.execute_query(count_query, [athlete_id, athlete_full_name])
        total_count = count_result[0]['count'] if count_result else 0
        
        return jsonify({
            'results': results,
            'athlete_id': athlete_id,
            'athlete_name': athlete_full_name,
            'page': page,
            'per_page': per_page,
            'total': total_count
        })
        
    except Exception as e:
        logging.error(f"Error fetching athlete results: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/athletes/by-name/results', methods=['GET'])
@firebase_auth_required
@limiter.limit("100 per hour")
def get_athlete_results_by_name():
    """Get all results for a specific athlete by name (supports partial matching)"""
    try:
        athlete_name = request.args.get('name', '').strip()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))
        
        if not athlete_name or len(athlete_name) < 2:
            return jsonify({'error': 'Athlete name must be at least 2 characters'}), 400
        
        offset = (page - 1) * per_page
        
        # Optimized query - search in results.athlete_name directly (fastest)
        query = """
          SELECT r.*, 
                 r.athlete_name, 
                 COALESCE(a.country_code, r.nationality) as athlete_country,
                 c.start_date as race_date, 
                 COALESCE(ra.race_type, 'Final') as race_type, 
                 e.event_name, e.discipline_code,
                 COALESCE(d.discipline_name, e.event_name) as discipline_name,
                 COALESCE(d.category, 'Track & Field') as category, 
                 c.name as competition_name
          FROM results r
          JOIN races ra ON r.race_id = ra.id
          JOIN events e ON ra.event_id = e.id
          JOIN competitions c ON ra.competition_id = c.id
          LEFT JOIN athletes a ON a.id = r.athlete_id
          LEFT JOIN disciplines d ON e.discipline_code = d.discipline_code
          WHERE r.athlete_name ILIKE %s
          AND r.mark IS NOT NULL 
          AND r.mark != ''
          ORDER BY c.start_date DESC, r.place ASC
          LIMIT %s OFFSET %s
          """
        
        search_term = f"%{athlete_name}%"
        results = db.execute_query(query, [search_term, per_page, offset])
        
        if results is None:
            return jsonify({'error': 'Failed to fetch athlete results'}), 500
        
        # Get total count - simplified
        count_query = """
        SELECT COUNT(*) as count
        FROM results
        WHERE athlete_name ILIKE %s
        AND mark IS NOT NULL 
        AND mark != ''
        """
        count_result = db.execute_query(count_query, [search_term])
        total_count = count_result[0]['count'] if count_result else 0
        
        return jsonify({
            'results': results,
            'athlete_name': athlete_name,
            'page': page,
            'per_page': per_page,
            'total': total_count
        })
        
    except Exception as e:
        logging.error(f"Error fetching athlete results by name: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/stats', methods=['GET'])
@firebase_auth_required
@limiter.limit("50 per hour")
def get_stats():
    """Get database statistics"""
    try:
        # Get counts for different entities
        competitions_result = db.execute_query("SELECT COUNT(*) as count FROM competitions")
        athletes_result = db.execute_query("SELECT COUNT(*) as count FROM athletes")
        results_result = db.execute_query("SELECT COUNT(*) as count FROM results")
        events_result = db.execute_query("SELECT COUNT(*) as count FROM events")
        
        # Check if queries returned results
        if not competitions_result or not athletes_result or not results_result or not events_result:
            logging.error("One or more stat queries returned None")
            return jsonify({'error': 'Database query failed'}), 500
        
        return jsonify({
            'competitions': competitions_result[0]['count'] if competitions_result else 0,
            'athletes': athletes_result[0]['count'] if athletes_result else 0,
            'results': results_result[0]['count'] if results_result else 0,
            'events': events_result[0]['count'] if events_result else 0
        })
        
    except Exception as e:
        logging.error(f"Error fetching stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        if db.connect():
            db.disconnect()
            return jsonify({'status': 'healthy', 'database': 'connected'})
        else:
            return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 500
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/api/optimize', methods=['GET'])
@firebase_auth_required
@limiter.limit("10 per hour")
def get_optimization_recommendations():
    """Get database optimization recommendations"""
    recommendations = {
        "database_indexes": [
            "CREATE INDEX IF NOT EXISTS idx_athletes_full_name ON athletes(full_name);",
            "CREATE INDEX IF NOT EXISTS idx_athletes_country_code ON athletes(country_code);",
            "CREATE INDEX IF NOT EXISTS idx_competitions_start_date ON competitions(start_date);",
            "CREATE INDEX IF NOT EXISTS idx_competitions_name ON competitions(name);",
            "CREATE INDEX IF NOT EXISTS idx_results_athlete_id ON results(athlete_id);",
            "CREATE INDEX IF NOT EXISTS idx_results_race_id ON results(race_id);",
            "CREATE INDEX IF NOT EXISTS idx_races_competition_id ON races(competition_id);",
            "CREATE INDEX IF NOT EXISTS idx_races_event_id ON races(event_id);",
            "CREATE INDEX IF NOT EXISTS idx_events_discipline_code ON events(discipline_code);"
        ],
        "performance_tips": [
            "Use pagination with reasonable page sizes (50-200 items)",
            "Implement search debouncing (300ms delay)",
            "Cache frequently accessed data client-side",
            "Use server-side sorting and filtering",
            "Limit result sets with proper WHERE clauses",
            "Use database indexes for common search patterns"
        ],
        "rate_limits": {
            "athletes": "200 requests per hour",
            "competitions": "100 requests per hour", 
            "results": "100 requests per hour",
            "search": "300 requests per hour"
        }
    }
    
    return jsonify(recommendations)

@app.route('/api/test', methods=['GET', 'POST', 'OPTIONS'])
def test_cors():
    """Test CORS endpoint"""
    return jsonify({'message': 'CORS is working', 'timestamp': '2025-01-06'})

@app.route('/api/debug/countries', methods=['GET'])
def debug_countries():
    """Debug endpoint to check available countries"""
    try:
        query = "SELECT DISTINCT code, name FROM countries WHERE name ILIKE '%singapore%' OR code ILIKE '%sg%' OR code ILIKE '%sin%' ORDER BY name"
        singapore_countries = db.execute_query(query)
        
        query2 = "SELECT COUNT(*) as total_athletes FROM athletes"
        total_athletes = db.execute_query(query2)[0]['total_athletes'] if db.execute_query(query2) else 0
        
        query3 = "SELECT DISTINCT country_code, COUNT(*) as athlete_count FROM athletes GROUP BY country_code ORDER BY athlete_count DESC LIMIT 10"
        top_countries = db.execute_query(query3)
        
        return jsonify({
            'singapore_countries': singapore_countries,
            'total_athletes': total_athletes,
            'top_countries': top_countries
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/singapore-athletes', methods=['GET'])
def debug_singapore_athletes():
    """Debug endpoint to check Singapore athletes"""
    try:
        query = """
        SELECT a.*, co.name as country_name
        FROM athletes a
        LEFT JOIN countries co ON a.country_code = co.code
        WHERE a.country_code ILIKE '%sg%' 
        OR a.country_code ILIKE '%sin%'
        OR co.name ILIKE '%singapore%'
        OR a.full_name ILIKE '%singapore%'
        LIMIT 20
        """
        singapore_athletes = db.execute_query(query)
        
        return jsonify({
            'singapore_athletes': singapore_athletes,
            'count': len(singapore_athletes) if singapore_athletes else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/singapore/summary', methods=['GET'])
@firebase_auth_required
@limiter.limit("200 per hour")
def get_singapore_summary():
    """Get Singapore summary statistics (fast query)"""
    try:
        # Singapore athletes count
        singapore_athletes_query = """
        SELECT COUNT(*) as count
        FROM athletes a
        WHERE a.country_code = 'SGP'
        """
        total_athletes = db.execute_query(singapore_athletes_query)[0]['count'] if db.execute_query(singapore_athletes_query) else 0

        # Singapore athletes with results - optimized
        singapore_with_results_query = """
        SELECT COUNT(DISTINCT full_name) as count
        FROM (
            SELECT a.full_name
            FROM athletes a
            JOIN results r ON a.id = r.athlete_id
            WHERE a.country_code = 'SGP'
            AND r.mark IS NOT NULL AND r.mark != ''
            
            UNION
            
            SELECT r.athlete_name as full_name
            FROM results r
            WHERE r.athlete_id IS NULL
            AND r.nationality = 'SGP'
            AND r.mark IS NOT NULL AND r.mark != ''
        ) combined
        """
        athletes_with_results = db.execute_query(singapore_with_results_query)[0]['count'] if db.execute_query(singapore_with_results_query) else 0

        # Singapore competitions count
        singapore_competitions_query = """
        SELECT COUNT(*) as count
        FROM competitions c
        WHERE c.country_code = 'SGP'
        """
        total_competitions = db.execute_query(singapore_competitions_query)[0]['count'] if db.execute_query(singapore_competitions_query) else 0

        # Singapore results count - optimized
        singapore_results_query = """
        SELECT COUNT(*) as count
        FROM results r
        LEFT JOIN athletes a ON a.id = r.athlete_id
        WHERE (a.country_code = 'SGP' OR r.nationality = 'SGP')
        AND r.mark IS NOT NULL 
        AND r.mark != ''
        """
        total_results = db.execute_query(singapore_results_query)[0]['count'] if db.execute_query(singapore_results_query) else 0

        # Gender distribution
        gender_query = """
        SELECT 
            CASE 
                WHEN LOWER(gender) = 'm' OR gender = 'male' THEN 'Male'
                WHEN LOWER(gender) = 'f' OR gender = 'female' THEN 'Female'
                ELSE COALESCE(gender, 'Unknown')
            END as gender_category,
            COUNT(*) as count
        FROM athletes a
        WHERE a.country_code = 'SGP'
        GROUP BY 
            CASE 
                WHEN LOWER(gender) = 'm' OR gender = 'male' THEN 'Male'
                WHEN LOWER(gender) = 'f' OR gender = 'female' THEN 'Female'
                ELSE COALESCE(gender, 'Unknown')
            END
        ORDER BY count DESC
        """
        gender_data = db.execute_query(gender_query) or []

        return jsonify({
            'total_athletes': total_athletes,
            'athletes_with_results': athletes_with_results,
            'total_competitions': total_competitions,
            'total_results': total_results,
            'gender_distribution': gender_data
        })

    except Exception as e:
        logging.error(f"Error fetching Singapore summary: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/singapore/top-athletes', methods=['GET'])
@firebase_auth_required
@limiter.limit("100 per hour")
def get_singapore_top_athletes():
    """Get top Singapore athletes (separate endpoint for progressive loading)"""
    try:
        query = """
        WITH singapore_results AS (
            SELECT 
                a.full_name,
                a.country_code,
                r.id as result_id,
                ra.competition_id
            FROM athletes a
            JOIN results r ON a.id = r.athlete_id
            JOIN races ra ON r.race_id = ra.id
            WHERE a.country_code = 'SGP'
            AND r.mark IS NOT NULL AND r.mark != ''
            
            UNION ALL
            
            SELECT 
                r.athlete_name as full_name,
                r.nationality as country_code,
                r.id as result_id,
                ra.competition_id
            FROM results r
            JOIN races ra ON r.race_id = ra.id
            WHERE r.athlete_id IS NULL
            AND r.nationality = 'SGP'
            AND r.mark IS NOT NULL AND r.mark != ''
        )
        SELECT 
            full_name,
            country_code,
            COUNT(result_id) as result_count,
            COUNT(DISTINCT competition_id) as competition_count
        FROM singapore_results
        GROUP BY full_name, country_code
        ORDER BY result_count DESC
        LIMIT 10
        """
        
        top_athletes = db.execute_query(query) or []
        return jsonify(top_athletes)

    except Exception as e:
        logging.error(f"Error fetching top Singapore athletes: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/singapore/disciplines', methods=['GET'])
@firebase_auth_required
@limiter.limit("100 per hour")
def get_singapore_disciplines():
    """Get Singapore discipline breakdown (separate endpoint)"""
    try:
        query = """
        SELECT 
            COALESCE(d.discipline_name, e.event_name) as discipline_name,
            COALESCE(d.category, 'Track & Field') as category,
            COUNT(DISTINCT r.athlete_name) as athlete_count,
            COUNT(r.id) as result_count
        FROM results r
        JOIN races ra ON r.race_id = ra.id
        JOIN events e ON ra.event_id = e.id
        LEFT JOIN athletes a ON a.id = r.athlete_id
        LEFT JOIN disciplines d ON e.discipline_code = d.discipline_code
        WHERE (a.country_code = 'SGP' OR r.nationality = 'SGP')
        AND r.mark IS NOT NULL 
        AND r.mark != ''
        GROUP BY COALESCE(d.discipline_name, e.event_name), COALESCE(d.category, 'Track & Field')
        HAVING COUNT(r.id) > 0
        ORDER BY result_count DESC
        LIMIT 10
        """
        
        disciplines = db.execute_query(query) or []
        return jsonify(disciplines)

    except Exception as e:
        logging.error(f"Error fetching Singapore disciplines: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/singapore/timeline', methods=['GET'])
@firebase_auth_required
@limiter.limit("100 per hour")
def get_singapore_timeline():
    """Get Singapore activity timeline (separate endpoint)"""
    try:
        query = """
        SELECT 
            EXTRACT(YEAR FROM c.start_date) as year,
            COUNT(DISTINCT c.id) as competition_count,
            COUNT(DISTINCT ra.id) as race_count,
            COUNT(r.id) as result_count
        FROM competitions c
        LEFT JOIN races ra ON c.id = ra.competition_id
        LEFT JOIN results r ON ra.id = r.race_id AND r.mark IS NOT NULL AND r.mark != ''
        WHERE c.country_code = 'SGP'
        AND c.start_date >= CURRENT_DATE - INTERVAL '5 years'
        GROUP BY EXTRACT(YEAR FROM c.start_date)
        ORDER BY year DESC
        """
        
        timeline = db.execute_query(query) or []
        return jsonify(timeline)

    except Exception as e:
        logging.error(f"Error fetching Singapore timeline: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/singapore/regional-comparison', methods=['GET'])
@firebase_auth_required
@limiter.limit("100 per hour")
def get_singapore_regional_comparison():
    """Get regional comparison (separate endpoint)"""
    try:
        query = """
        WITH country_results AS (
            SELECT 
                a.country_code,
                a.full_name,
                r.id as result_id
            FROM athletes a
            JOIN results r ON a.id = r.athlete_id
            WHERE a.country_code IN ('SGP', 'MAS', 'THA', 'PHI', 'INA', 'VNM')
            AND r.mark IS NOT NULL AND r.mark != ''
            
            UNION ALL
            
            SELECT 
                r.nationality as country_code,
                r.athlete_name as full_name,
                r.id as result_id
            FROM results r
            WHERE r.athlete_id IS NULL
            AND r.nationality IN ('SGP', 'MAS', 'THA', 'PHI', 'INA', 'VNM')
            AND r.mark IS NOT NULL AND r.mark != ''
        )
        SELECT 
            cr.country_code,
            co.name as country_name,
            COUNT(DISTINCT cr.full_name) as athlete_count,
            COUNT(cr.result_id) as result_count
        FROM country_results cr
        LEFT JOIN countries co ON cr.country_code = co.code
        GROUP BY cr.country_code, co.name
        ORDER BY result_count DESC
        """
        
        comparison = db.execute_query(query) or []
        return jsonify(comparison)

    except Exception as e:
        logging.error(f"Error fetching regional comparison: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/singapore/stats', methods=['GET'])
@firebase_auth_required
@limiter.limit("100 per hour")
def get_singapore_stats():
    """Get comprehensive Singapore athletics statistics for dashboard charts"""
    try:
        # Singapore athletes count
        singapore_athletes_query = """
        SELECT COUNT(*) as count
        FROM athletes a
        LEFT JOIN countries co ON a.country_code = co.code
        WHERE a.country_code = 'SGP'
        """
        singapore_athletes_count = db.execute_query(singapore_athletes_query)[0]['count'] if db.execute_query(singapore_athletes_query) else 0

        # Singapore athletes with results - optimized with UNION
        singapore_with_results_query = """
        SELECT COUNT(DISTINCT full_name) as count
        FROM (
            SELECT a.full_name
            FROM athletes a
            JOIN results r ON a.id = r.athlete_id
            WHERE a.country_code = 'SGP'
            AND r.mark IS NOT NULL AND r.mark != ''
            
            UNION
            
            SELECT r.athlete_name as full_name
            FROM results r
            WHERE r.athlete_id IS NULL
            AND r.nationality = 'SGP'
            AND r.mark IS NOT NULL AND r.mark != ''
        ) combined
        """
        singapore_with_results_count = db.execute_query(singapore_with_results_query)[0]['count'] if db.execute_query(singapore_with_results_query) else 0

        # Singapore competitions count
        singapore_competitions_query = """
        SELECT COUNT(*) as count
        FROM competitions c
        WHERE c.country_code = 'SGP'
        """
        singapore_competitions_count = db.execute_query(singapore_competitions_query)[0]['count'] if db.execute_query(singapore_competitions_query) else 0

        # Singapore results count - optimized with simple OR in WHERE clause
        singapore_results_query = """
        SELECT COUNT(*) as count
        FROM results r
        LEFT JOIN athletes a ON a.id = r.athlete_id
        WHERE (a.country_code = 'SGP' OR r.nationality = 'SGP')
        AND r.mark IS NOT NULL 
        AND r.mark != ''
        """
        singapore_results_count = db.execute_query(singapore_results_query)[0]['count'] if db.execute_query(singapore_results_query) else 0

        # Singapore athletes by gender
        singapore_gender_query = """
        SELECT 
            CASE 
                WHEN LOWER(gender) = 'm' OR gender = 'male' THEN 'Male'
                WHEN LOWER(gender) = 'f' OR gender = 'female' THEN 'Female'
                ELSE COALESCE(gender, 'Unknown')
            END as gender_category,
            COUNT(*) as count
        FROM athletes a
        WHERE a.country_code = 'SGP'
        GROUP BY 
            CASE 
                WHEN LOWER(gender) = 'm' OR gender = 'male' THEN 'Male'
                WHEN LOWER(gender) = 'f' OR gender = 'female' THEN 'Female'
                ELSE COALESCE(gender, 'Unknown')
            END
        ORDER BY count DESC
        """
        singapore_gender_data = db.execute_query(singapore_gender_query) or []

        # Singapore athletes by discipline - optimized
        singapore_disciplines_query = """
        SELECT 
            COALESCE(d.discipline_name, e.event_name) as discipline_name,
            COALESCE(d.category, 'Track & Field') as category,
            COUNT(DISTINCT r.athlete_name) as athlete_count,
            COUNT(r.id) as result_count
        FROM results r
        JOIN races ra ON r.race_id = ra.id
        JOIN events e ON ra.event_id = e.id
        LEFT JOIN athletes a ON a.id = r.athlete_id
        LEFT JOIN disciplines d ON e.discipline_code = d.discipline_code
        WHERE (a.country_code = 'SGP' OR r.nationality = 'SGP')
        AND r.mark IS NOT NULL 
        AND r.mark != ''
        GROUP BY COALESCE(d.discipline_name, e.event_name), COALESCE(d.category, 'Track & Field')
        HAVING COUNT(r.id) > 0
        ORDER BY result_count DESC
        LIMIT 10
        """
        singapore_disciplines_data = db.execute_query(singapore_disciplines_query) or []

        # Singapore competitions timeline (last 5 years)
        singapore_timeline_query = """
        SELECT 
            EXTRACT(YEAR FROM c.start_date) as year,
            COUNT(DISTINCT c.id) as competition_count,
            COUNT(DISTINCT ra.id) as race_count,
            COUNT(r.id) as result_count
        FROM competitions c
        LEFT JOIN races ra ON c.id = ra.competition_id
        LEFT JOIN results r ON ra.id = r.race_id AND r.mark IS NOT NULL AND r.mark != ''
        WHERE c.country_code = 'SGP'
        AND c.start_date >= CURRENT_DATE - INTERVAL '5 years'
        GROUP BY EXTRACT(YEAR FROM c.start_date)
        ORDER BY year DESC
        """
        singapore_timeline_data = db.execute_query(singapore_timeline_query) or []

        # Top Singapore athletes by results - optimized with UNION to avoid slow OR joins
        top_singapore_athletes_query = """
        WITH singapore_results AS (
            -- Results with athlete_id mapping
            SELECT 
                a.full_name,
                a.country_code,
                r.id as result_id,
                ra.competition_id
            FROM athletes a
            JOIN results r ON a.id = r.athlete_id
            JOIN races ra ON r.race_id = ra.id
            WHERE a.country_code = 'SGP'
            AND r.mark IS NOT NULL AND r.mark != ''
            
            UNION ALL
            
            -- Results without athlete_id (by name match)
            SELECT 
                r.athlete_name as full_name,
                r.nationality as country_code,
                r.id as result_id,
                ra.competition_id
            FROM results r
            JOIN races ra ON r.race_id = ra.id
            WHERE r.athlete_id IS NULL
            AND r.nationality = 'SGP'
            AND r.mark IS NOT NULL AND r.mark != ''
        )
        SELECT 
            full_name,
            country_code,
            COUNT(result_id) as result_count,
            COUNT(DISTINCT competition_id) as competition_count
        FROM singapore_results
        GROUP BY full_name, country_code
        ORDER BY result_count DESC
        LIMIT 10
        """
        top_singapore_athletes = db.execute_query(top_singapore_athletes_query) or []

        # Singapore vs other countries comparison - optimized
        countries_comparison_query = """
        WITH country_results AS (
            SELECT 
                a.country_code,
                a.full_name,
                r.id as result_id
            FROM athletes a
            JOIN results r ON a.id = r.athlete_id
            WHERE a.country_code IN ('SGP', 'MAS', 'THA', 'PHI', 'INA', 'VNM')
            AND r.mark IS NOT NULL AND r.mark != ''
            
            UNION ALL
            
            SELECT 
                r.nationality as country_code,
                r.athlete_name as full_name,
                r.id as result_id
            FROM results r
            WHERE r.athlete_id IS NULL
            AND r.nationality IN ('SGP', 'MAS', 'THA', 'PHI', 'INA', 'VNM')
            AND r.mark IS NOT NULL AND r.mark != ''
        )
        SELECT 
            cr.country_code,
            co.name as country_name,
            COUNT(DISTINCT cr.full_name) as athlete_count,
            COUNT(cr.result_id) as result_count
        FROM country_results cr
        LEFT JOIN countries co ON cr.country_code = co.code
        GROUP BY cr.country_code, co.name
        ORDER BY result_count DESC
        """
        countries_comparison_data = db.execute_query(countries_comparison_query) or []

        return jsonify({
            'singapore_summary': {
                'total_athletes': singapore_athletes_count,
                'athletes_with_results': singapore_with_results_count,
                'total_competitions': singapore_competitions_count,
                'total_results': singapore_results_count
            },
            'gender_distribution': singapore_gender_data,
            'discipline_breakdown': singapore_disciplines_data,
            'timeline_data': singapore_timeline_data,
            'top_athletes': top_singapore_athletes,
            'regional_comparison': countries_comparison_data
        })

    except Exception as e:
        logging.error(f"Error fetching Singapore stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@https_fn.on_request(region="asia-southeast1")
def athletics_api(req: https_fn.Request) -> https_fn.Response:
    """Main Firebase Function entry point"""
    with app.request_context(req.environ):
        return app.full_dispatch_request()

if __name__ == '__main__':
    app.run(debug=True, port=5001)