# Logseq Pankti

A Logseq plugin for searching and adding Panktis (verses) from Sri Guru Granth Sahib Ji database to your Logseq notes.

## Features

- Advanced search capabilities for finding Gurbani verses:
  - Full-text search with prefix fallback
  - Fuzzy search for approximate matches
  - First-consonant search (useful for Punjabi transliterations)
- Integration with Logseq as a plugin
- SQLite database for efficient storage and retrieval
- Cross-platform compatibility

## Technical Stack

- **Frontend**:
  - TypeScript with Logseq Plugin API
  - Parcel for bundling
  - HTML/CSS for UI

- **Backend**:
  - Python Flask server
  - SQLite database
  - Custom search algorithms including fuzzy matching
  - CORS enabled for local development

## Installation

1. Clone this repository
2. Install Python dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install flask flask-cors fuzzywuzzy sqlite3
   ```
3. Install Node.js dependencies:
   ```bash
   npm install
   ```

## Development

1. Start the Python backend server:
   ```bash
   python server.py
   ```
   The server will run on http://localhost:3033

2. Start the frontend development server:
   ```bash
   npm run dev
   ```

## Building

To build the plugin for production:
```bash
npm run build
```

## Database

The application uses `gurbani.db` SQLite database which contains the verses from Sri Guru Granth Sahib Ji. The database is optimized with full-text search capabilities for efficient querying.

## License

MIT License - See LICENSE file for details

## Author

harsh@aka.al