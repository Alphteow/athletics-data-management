import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config
import logging

class Database:
    def __init__(self):
        self.config = Config()
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                host=self.config.DB_HOST,
                port=self.config.DB_PORT,
                database=self.config.DB_NAME,
                user=self.config.DB_USER,
                password=self.config.DB_PASSWORD,
                cursor_factory=RealDictCursor
            )
            self.cursor = self.connection.cursor()
            logging.info("Database connection established successfully")
            return True
        except Exception as e:
            logging.error(f"Database connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logging.info("Database connection closed")
    
    def execute_query(self, query, params=None):
        """Execute a SELECT query and return results"""
        try:
            if not self.connection or self.connection.closed:
                self.connect()
            
            self.cursor.execute(query, params)
            results = self.cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logging.error(f"Query execution failed: {e}")
            return None
    
    def execute_insert(self, query, params=None):
        """Execute an INSERT query"""
        try:
            if not self.connection or self.connection.closed:
                self.connect()
            
            self.cursor.execute(query, params)
            self.connection.commit()
            return self.cursor.rowcount
        except Exception as e:
            logging.error(f"Insert execution failed: {e}")
            self.connection.rollback()
            return 0
    
    def get_competitions(self, limit=50, offset=0, search=None):
        """Get competitions with optional search"""
        query = """
        SELECT c.*, co.name as country_name, rc.name as ranking_category_name
        FROM competitions c
        LEFT JOIN countries co ON c.country_code = co.code
        LEFT JOIN ranking_categories rc ON c.ranking_category_id = rc.id
        """
        
        params = []
        if search:
            query += " WHERE c.name ILIKE %s OR c.venue ILIKE %s OR co.name ILIKE %s"
            params = [f"%{search}%", f"%{search}%", f"%{search}%"]
        
        query += " ORDER BY c.start_date DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        return self.execute_query(query, params)
    
    def get_athletes(self, limit=50, offset=0, search=None):
        """Get athletes with optional search"""
        query = """
        SELECT a.*, co.name as country_name
        FROM athletes a
        LEFT JOIN countries co ON a.country_code = co.code
        """
        
        params = []
        if search:
            query += " WHERE a.full_name ILIKE %s OR a.family_name ILIKE %s OR a.given_name ILIKE %s OR co.name ILIKE %s"
            params = [f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"]
        
        query += " ORDER BY a.full_name LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        return self.execute_query(query, params)
    
    def get_results_by_competition(self, competition_id, limit=100, offset=0):
        """Get results for a specific competition"""
        query = """
        SELECT r.*, a.full_name as athlete_name, a.country_code as athlete_country,
               ra.race_date, ra.race_type, e.event_title, e.discipline_code,
               d.discipline_name, d.category
        FROM results r
        JOIN races ra ON r.race_id = ra.id
        JOIN events e ON ra.event_id = e.id
        JOIN athletes a ON r.athlete_id = a.id
        LEFT JOIN disciplines d ON e.discipline_code = d.discipline_code
        WHERE ra.competition_id = %s
        ORDER BY ra.race_date DESC, r.place ASC
        LIMIT %s OFFSET %s
        """
        
        return self.execute_query(query, [competition_id, limit, offset])
    
    def get_results_by_athlete(self, athlete_id, limit=50, offset=0):
        """Get results for a specific athlete"""
        query = """
        SELECT r.*, ra.race_date, ra.race_type, e.event_title, e.discipline_code,
               d.discipline_name, d.category, c.name as competition_name, c.venue
        FROM results r
        JOIN races ra ON r.race_id = ra.id
        JOIN events e ON ra.event_id = e.id
        JOIN competitions c ON ra.competition_id = c.id
        LEFT JOIN disciplines d ON e.discipline_code = d.discipline_code
        WHERE r.athlete_id = %s
        ORDER BY ra.race_date DESC
        LIMIT %s OFFSET %s
        """
        
        return self.execute_query(query, [athlete_id, limit, offset])
    
    def get_disciplines(self):
        """Get all disciplines"""
        query = "SELECT * FROM disciplines ORDER BY discipline_name"
        return self.execute_query(query)
    
    def get_countries(self):
        """Get all countries"""
        query = "SELECT * FROM countries ORDER BY name"
        return self.execute_query(query)
