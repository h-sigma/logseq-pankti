from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from fuzzywuzzy import fuzz
import heapq
import time
import re

app = Flask(__name__)
CORS(app)

def normalize_ascii(text):
    """Remove everything except alphabet characters and spaces"""
    return re.sub(r'[^a-zA-Z\s]', '', text)

def extract_first_consonant(text):
    """Extract first consonant(s) of each word based on Punjabi transliteration rules.
    
    Rules:
    1. For consonant clusters like 'bh', 'gh', 'sh', 'ch', 'th', 'dh', 'ph', take both letters
    2. For single consonants, take just one letter
    3. Skip vowels at the start of words
    
    Examples:
    - sagar -> s
    - bhee -> bh
    - shromni -> sh
    - adhyatam -> a
    """
    if not text:
        return ""
        
    # Define Punjabi consonant clusters
    clusters = ['bh', 'gh', 'sh', 'ch', 'th', 'dh', 'ph', 'jh', 'kh']
    # Define vowels that can start words
    vowels = ['a', 'e', 'i', 'o', 'u']
    
    def extract_from_word(word):
        if not word:
            return ""
        
        # Convert to lowercase for comparison
        word = word.lower()
        
        # If word starts with a vowel, return just that
        if word[0] in vowels:
            return word[0]
            
        # Check for consonant clusters
        if len(word) >= 2:
            first_two = word[:2]
            if first_two in clusters:
                return first_two
        
        # Return first letter for all other cases
        return word[0]
    
    words = text.split()
    first_consonants = [extract_from_word(word) for word in words if word]
    result = " ".join(first_consonants)
    
    # Normalize the result to remove any non-ASCII characters
    normalized = normalize_ascii(result)
    if normalized != result:
        print(f"Normalized result from '{result}' -> '{normalized}'")
    
    return normalized

def init_db_functions(db):
    """Initialize custom SQLite functions"""
    db.create_function("extract_consonants", 1, extract_first_consonant)

def log_sql(query, params=None):
    """Format and log SQL query"""
    if params:
        # Replace ? with actual values for logging
        for param in params:
            query = query.replace('?', repr(param), 1)
    print(f"Executing SQL: {query}")

def log_request(search_type, query, results_count, duration):
    """Log search request details"""
    print(f"\n{'='*50}")
    print(f"Search Type: {search_type}")
    print(f"Query: '{query}'")
    print(f"Results Found: {results_count}")
    print(f"Duration: {duration:.2f}s")
    print(f"{'='*50}\n")

def init_fts():
    print("\nInitializing FTS table...")
    with sqlite3.connect('gurbani.db') as conn:
        # Initialize custom functions
        init_db_functions(conn)
        
        cur = conn.cursor()
        
        # Drop existing FTS table to recreate with shabdID
        sql = 'DROP TABLE IF EXISTS ggs_fts'
        log_sql(sql)
        cur.execute(sql)
        
        # Create FTS virtual table with shabdID
        sql = '''
            CREATE VIRTUAL TABLE IF NOT EXISTS ggs_fts USING fts5(
                pageID, 
                pagelineID, 
                attributes, 
                punjabi, 
                translit,
                shabdID,
                content='ggs',
                content_rowid='rowid'
            )
        '''
        log_sql(sql)
        cur.execute(sql)
        
        # Check if FTS table needs to be populated
        sql = 'SELECT count(*) FROM ggs_fts'
        log_sql(sql)
        cur.execute(sql)
        count = cur.fetchone()[0]
        print(f"Current FTS entries: {count}")
        
        if count == 0:
            print("Populating FTS table...")
            # Populate FTS table with shabdID
            sql = '''
                INSERT INTO ggs_fts(
                    rowid, 
                    pageID, 
                    pagelineID, 
                    attributes, 
                    punjabi, 
                    translit,
                    shabdID
                )
                SELECT 
                    rowid, 
                    pageID, 
                    pagelineID, 
                    attributes, 
                    punjabi, 
                    translit,
                    shabdID
                FROM ggs
            '''
            log_sql(sql)
            cur.execute(sql)
            conn.commit()
            print("FTS table populated successfully")
    print("Initialization complete!\n")

def fuzzy_search(query, cur):
    """Perform fuzzy search on the entire database"""
    print(f"\nFuzzy Search Details:")
    print(f"{'='*50}")
    print(f"Input query: '{query}'")
    
    # Clean the query text
    original_query = query
    query = ''.join(c for c in query if c.isalnum() or c.isspace())
    if query != original_query:
        print(f"Cleaned query: '{query}'")
        print(f"Removed characters: '{set(original_query) - set(query)}'")
    
    if not query.strip():
        print("Empty query after cleaning")
        print("="*50)
        return []

    try:
        print("\nDatabase Query:")
        sql = '''
            SELECT 
                pageID, 
                pagelineID, 
                attributes, 
                punjabi, 
                translit,
                shabdID
            FROM ggs
            LIMIT 1000  # Limit initial search space
        '''
        log_sql(sql)
        cur.execute(sql)
        rows = cur.fetchall()
        print(f"Retrieved {len(rows)} rows for comparison")
        
        # Calculate fuzzy match scores
        matches = []
        for row in rows:
            translit_score = fuzz.ratio(query.lower(), row[4].lower())
            if translit_score > 60:  # Minimum similarity threshold
                heapq.heappush(matches, (-translit_score, row))
        
        # Get top 10 matches
        results = []
        for _ in range(min(10, len(matches))):
            score, row = heapq.heappop(matches)
            results.append(row)
        
        print(f"\nSearch Results:")
        print(f"Found {len(results)} matches")
        
        if results:
            print("\nTop Matches (first 5):")
            for i, row in enumerate(results[:5], 1):
                print(f"{i}. Score: {-matches[i-1][0]:3d} | Punjabi: {row[3][:30]:30} | Translit: {row[4][:30]}")
        
        print("="*50)
        return [
            {
                'pageID': row[0],
                'pagelineID': row[1],
                'attributes': row[2],
                'punjabi': row[3],
                'translit': row[4],
                'shabdID': row[5]
            }
            for row in results
        ]
    except Exception as e:
        print(f"Error in fuzzy search: {str(e)}")
        return []

def first_each_word_search(query, cur):
    """Extract first consonant of each word and search with % between them"""
    print(f"\nFirst Consonant Search Details:")
    print(f"{'='*50}")
    print(f"Input query: '{query}'")
    
    # Split query into words and extract consonants
    consonants = extract_first_consonant(query).split()
    print(f"\nConsonant Analysis:")
    print(f"Total words processed: {len(query.split())}")
    print(f"Consonants extracted: {consonants}")
    
    if not consonants:
        print("No valid consonants found")
        print("="*50)
        return []
    
    # Create pattern to match against first consonants of translit
    pattern = ' '.join(consonants)
    print(f"\nSearch Pattern:")
    print(f"Pattern for matching: '{pattern}'")
    print("Will match these consonants against first consonant(s) of each word")
    
    # Search using the custom function
    print("\nDatabase Query:")
    sql = '''
        WITH first_consonants AS (
            SELECT 
                pageID, 
                pagelineID, 
                attributes, 
                punjabi, 
                translit,
                shabdID,
                extract_consonants(translit) as consonants
            FROM ggs
        )
        SELECT 
            pageID, 
            pagelineID, 
            attributes, 
            punjabi, 
            translit,
            shabdID,
            consonants
        FROM first_consonants
        WHERE consonants LIKE ?
        LIMIT 10
    '''
    # Add % between each consonant and at start/end
    search_pattern = f'%{"%".join(consonants)}%'
    log_sql(sql, [search_pattern])
    cur.execute(sql, [search_pattern])
    
    rows = cur.fetchall()
    print(f"Found {len(rows)} matches")
    
    if rows:
        print("\nMatched Entries (first 5):")
        for i, row in enumerate(rows[:5], 1):
            print(f"{i}. Punjabi: {row[3][:30]:30} | Translit: {row[4][:30]}")
            print(f"   Consonants: {row[6]}")
    
    print("="*50)
    return [
        {
            'pageID': row[0],
            'pagelineID': row[1],
            'attributes': row[2],
            'punjabi': row[3],
            'translit': row[4],
            'shabdID': row[5]
        }
        for row in rows
    ]

def text_search(query, cur):
    """Full text search with prefix fallback and LIKE operator"""
    print(f"\nText Search Details:")
    print(f"{'='*50}")
    print(f"Input query: '{query}'")
    
    # Try exact match first
    print("\nStage 1: Exact Match")
    exact_sql = '''
        SELECT 
            pageID, 
            pagelineID, 
            attributes, 
            punjabi, 
            translit,
            shabdID
        FROM ggs_fts
        WHERE translit MATCH ?
        ORDER BY rank
        LIMIT 10
    '''
    exact_term = f'"{query}"'
    print(f"Using FTS5 with exact match: '{exact_term}'")
    log_sql(exact_sql, [exact_term])
    cur.execute(exact_sql, [exact_term])
    rows = cur.fetchall()
    
    # If no results, try prefix search
    if not rows:
        print("\nStage 2: Prefix Match")
        prefix_term = f'{query}*'
        print(f"No exact matches found, trying prefix search: '{prefix_term}'")
        log_sql(exact_sql, [prefix_term])
        cur.execute(exact_sql, [prefix_term])
        rows = cur.fetchall()
    
    # If still no results, fall back to LIKE
    if not rows:
        print("\nStage 3: LIKE Operator")
        like_sql = '''
            SELECT 
                pageID, 
                pagelineID, 
                attributes, 
                punjabi, 
                translit,
                shabdID
            FROM ggs
            WHERE translit LIKE ?
            LIMIT 10
        '''
        like_term = f'%{query}%'
        print(f"No prefix matches found, using LIKE operator: '{like_term}'")
        log_sql(like_sql, [like_term])
        cur.execute(like_sql, [like_term])
        rows = cur.fetchall()
    
    print(f"\nSearch Results:")
    print(f"Found {len(rows)} matches")
    
    if rows:
        print("\nMatched Entries (first 5):")
        for i, row in enumerate(rows[:5], 1):
            print(f"{i}. Punjabi: {row[3][:30]:30} | Translit: {row[4][:30]}")
    
    print("="*50)
    return [
        {
            'pageID': row[0],
            'pagelineID': row[1],
            'attributes': row[2],
            'punjabi': row[3],
            'translit': row[4],
            'shabdID': row[5]
        }
        for row in rows
    ]

@app.route('/text')
def handle_text_search():
    start_time = time.time()
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    try:
        with sqlite3.connect('gurbani.db') as conn:
            # Initialize custom functions
            init_db_functions(conn)
            
            cur = conn.cursor()
            results = text_search(query, cur)
            duration = time.time() - start_time
            log_request("Text Search", query, len(results), duration)
            return jsonify(results)
    except Exception as e:
        print(f"Text search error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/fuzzy')
def handle_fuzzy_search():
    start_time = time.time()
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    try:
        with sqlite3.connect('gurbani.db') as conn:
            # Initialize custom functions
            init_db_functions(conn)
            
            cur = conn.cursor()
            results = fuzzy_search(query, cur)
            duration = time.time() - start_time
            log_request("Fuzzy Search", query, len(results), duration)
            return jsonify(results)
    except Exception as e:
        print(f"Fuzzy search error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/first_each_word')
def handle_first_each_word():
    start_time = time.time()
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    try:
        with sqlite3.connect('gurbani.db') as conn:
            # Initialize custom functions
            init_db_functions(conn)
            
            cur = conn.cursor()
            results = first_each_word_search(query, cur)
            duration = time.time() - start_time
            log_request("First Each Word Search", query, len(results), duration)
            return jsonify(results)
    except Exception as e:
        print(f"First each word search error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_shabad/<shabdID>')
def get_shabad(shabdID):
    """Get all lines from a shabad by its ID"""
    start = time.time()
    shabdID = int(shabdID)
    
    try:
        with sqlite3.connect('gurbani.db') as conn:
            init_db_functions(conn)
            cur = conn.cursor()
            
            sql = '''
                SELECT 
                    pageID, 
                    pagelineID, 
                    attributes, 
                    punjabi, 
                    translit,
                    shabdID
                FROM ggs 
                WHERE shabdID = ?
                ORDER BY pagelineID
            '''
            log_sql(sql, [shabdID])
            cur.execute(sql, [shabdID])
            rows = cur.fetchall()
            
            results = [
                {
                    'pageID': row[0],
                    'pagelineID': row[1],
                    'attributes': row[2],
                    'punjabi': row[3],
                    'translit': row[4],
                    'shabdID': row[5]
                }
                for row in rows
            ]
            
            duration = time.time() - start
            log_request("get_shabad", shabdID, len(results), duration)
            return jsonify(results)
            
    except Exception as e:
        print(f"Error getting shabad: {str(e)}")
        return jsonify([])

if __name__ == '__main__':
    init_fts()
    print("\nServer starting on http://localhost:3033")
    app.run(port=3033, debug=True)
