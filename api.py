from flask import Flask, request, jsonify
from flask_compress import Compress
import pymysql
import os
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
Compress(app)  # Enable GZIP compression for all responses

# --- Logging Configuration ---
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'ERROR').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.ERROR),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Logs to stdout (Docker captures this)
    ]
)
logger = logging.getLogger(__name__)

logger.info(f"Application starting with log level: {LOG_LEVEL}")

# --- IMPORTANT: CONFIGURE YOUR DATABASE HERE ---
db_config = {
    'host': os.environ.get("DB_HOST", "192.168.0.10"),
    'user': os.environ.get("DB_USER", 'barcodescanner'),
    'password': os.environ.get("DB_PWD", 'superPassword'),
    'database': os.environ.get("DB_NAME", 'somedb'),
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    """Establishes a connection to the database."""
    try:
        logger.debug(f"Attempting to connect to database at {db_config['host']}")
        conn = pymysql.connect(**db_config)
        logger.debug("Database connection established successfully")
        return conn
    except pymysql.MySQLError as e:
        logger.error(f"Error connecting to MySQL: {e}")
        return None

@app.route('/sync', methods=['POST'])
def sync_items():
    """
    Receives a list of scanned items and inserts them into the database.
    """
    logger.debug("Received sync request")
    items = request.get_json()
    
    if not items:
        logger.warning("Sync request received with no items")
        return jsonify({"status": "error", "message": "No items provided"}), 400
    
    logger.info(f"Processing sync request with {len(items)} items")
    
    conn = get_db_connection()
    if conn is None:
        logger.error("Failed to establish database connection for sync")
        return jsonify({"status": "error", "message": "Database connection failed"}), 500
    
    try:
        with conn.cursor() as cursor:
            # Note: The table is 'bcode' and columns are 'dok', 'barcode', 'lot', 'rok', 'kol'
            sql = "INSERT INTO `bcode` (`dok`, `barcode`, `lot`, `rok`, `kol`) VALUES (%s, %s, %s, %s, %s)"
            
            # Prepare a list of tuples for executemany for efficiency
            item_tuples = []
            for item in items:
                item_tuples.append((
                    item.get('docNumber'),
                    item.get('barcode'),
                    item.get('lot'),
                    item.get('rok'),
                    item.get('quantity')
                ))
            
            if item_tuples:
                logger.debug(f"Inserting {len(item_tuples)} items into database")
                cursor.executemany(sql, item_tuples)
        
        conn.commit()
        logger.info(f"Successfully inserted {len(item_tuples)} items")
        return jsonify({"status": "success", "message": f"{len(item_tuples)} items synced"}), 200
    
    except pymysql.MySQLError as e:
        logger.error(f"Error during database insert: {e}")
        conn.rollback()
        return jsonify({"status": "error", "message": f"Database error: {e}"}), 500
    
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")

@app.route('/getart', methods=['GET'])
def get_articles():
    """
    Retrieve articles from your database.items table.
    Returns: JSON array of objects with barcode and naziv fields.
    """
    logger.debug("Received getart request")

    DB_ITEMS = os.environ.get("DB_ITEMS","somedb.tablewithitems")

    conn = get_db_connection()
    if conn is None:
        logger.error("Failed to establish database connection for getart")
        return jsonify({"status": "error", "message": "Database connection failed"}), 500
    
    try:
        with conn.cursor() as cursor:
            sql = f"SELECT barcode, naziv FROM {DB_ITEMS} where length(barcode) > 0"
            logger.debug("Executing query to retrieve articles")
            cursor.execute(sql)
            
            # Fetch all results
            results = cursor.fetchall()
            
            # Convert to list of dictionaries
            articles = []
            for row in results:
                articles.append({
                    "barcode": row['barcode'],
                    "naziv": row['naziv']
                })
            
            logger.info(f"Successfully retrieved {len(articles)} articles")
            return jsonify({
                "status": "success",
                "count": len(articles),
                "data": articles
            }), 200
    
    except pymysql.MySQLError as e:
        logger.error(f"Error during database query: {e}")
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")

if __name__ == '__main__':
    # Use FLASK_ENV environment variable to control debug mode
    # For production: FLASK_ENV=production
    # For development: FLASK_ENV=development (default if not set)
    flask_env = os.environ.get('FLASK_ENV', 'development')
    debug_mode = flask_env == 'development'
    
    logger.info(f"Starting Flask app in {flask_env} mode (debug={debug_mode})")
    
    # Runs the API on all available network interfaces on port 5000
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
