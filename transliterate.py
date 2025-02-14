import sqlite3
from aksharamukha import transliterate

def update_database():
    try:
        with sqlite3.connect('gurbani.db') as conn:
            cur = conn.cursor()
            
            # Add translit column if it doesn't exist
            try:
                cur.execute('ALTER TABLE ggs ADD COLUMN translit TEXT')
                print("Added translit column")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print("Column already exists, proceeding with update")
                else:
                    raise e
            
            # Get all rows that need transliteration
            cur.execute('SELECT rowid, punjabi FROM ggs WHERE translit IS NULL')
            rows = cur.fetchall()
            
            total = len(rows)
            print(f"Processing {total} rows...")
            
            # Update each row
            for i, (rowid, punjabi) in enumerate(rows, 1):
                if punjabi:
                    try:
                        translit = transliterate.process('Gurmukhi', 'RomanReadable', punjabi)
                        cur.execute('UPDATE ggs SET translit = ? WHERE rowid = ?', (translit, rowid))
                        
                        if i % 100 == 0:  # Progress update every 100 rows
                            print(f"Processed {i}/{total} rows")
                            conn.commit()  # Periodic commit
                    except Exception as e:
                        print(f"Error processing row {rowid}: {e}")
            
            conn.commit()
            print("Successfully updated all transliterations!")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    update_database()
