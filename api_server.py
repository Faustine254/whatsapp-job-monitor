"""
Flask API Server with WebSocket
Serves the web interface and provides real-time updates
"""

from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Initialize Flask app
app = Flask(__name__, static_folder='.')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
JOBS_FILE = "jobs_data.json"
jobs_data = []
monitoring_status = {
    "is_running": False,
    "started_at": None,
    "total_jobs": 0,
    "last_update": None
}

class JobFileHandler(FileSystemEventHandler):
    """Watch for changes in jobs_data.json"""
    def on_modified(self, event):
        if event.src_path.endswith(JOBS_FILE):
            print(f"📝 Jobs file updated")
            load_jobs()
            # Notify all connected clients
            socketio.emit('jobs_updated', {
                'jobs': jobs_data,
                'stats': get_stats()
            })

def load_jobs():
    """Load jobs from JSON file"""
    global jobs_data
    try:
        if Path(JOBS_FILE).exists():
            with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                jobs_data = json.load(f)
                monitoring_status['total_jobs'] = len(jobs_data)
                monitoring_status['last_update'] = datetime.now().isoformat()
                print(f"✓ Loaded {len(jobs_data)} jobs")
        else:
            jobs_data = []
            print("⚠ No jobs file found yet")
    except Exception as e:
        print(f"✗ Error loading jobs: {e}")
        jobs_data = []

def get_stats():
    """Calculate statistics from jobs"""
    if not jobs_data:
        return {
            "total": 0,
            "today": 0,
            "thisWeek": 0,
            "withImages": 0,
            "byType": {}
        }
    
    today = datetime.now().date()
    week_ago = datetime.now() - timedelta(days=7)
    
    stats = {
        "total": len(jobs_data),
        "today": 0,
        "thisWeek": 0,
        "withImages": 0,
        "byType": {}
    }
    
    for job in jobs_data:
        # Date-based counts
        try:
            job_date = datetime.fromisoformat(job['date']).date()
            if job_date == today:
                stats['today'] += 1
            if datetime.fromisoformat(job['date']) >= week_ago:
                stats['thisWeek'] += 1
        except:
            pass
        
        # Image count
        if job.get('hasImage'):
            stats['withImages'] += 1
        
        # Job type distribution
        job_type = job.get('type', 'unknown')
        stats['byType'][job_type] = stats['byType'].get(job_type, 0) + 1
    
    return stats

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def serve_index():
    """Serve the main HTML page"""
    return send_file('index.html')

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "jobs_loaded": len(jobs_data)
    })

@app.route('/api/jobs')
def get_jobs():
    """Get all jobs with optional filtering"""
    # Get query parameters
    date_from = request.args.get('dateFrom')
    date_to = request.args.get('dateTo')
    search = request.args.get('search', '').lower()
    job_type = request.args.get('type', 'all')
    
    filtered_jobs = jobs_data.copy()
    
    # Apply filters
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from)
            filtered_jobs = [j for j in filtered_jobs 
                           if datetime.fromisoformat(j['date']) >= date_from_obj]
        except:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to)
            filtered_jobs = [j for j in filtered_jobs 
                           if datetime.fromisoformat(j['date']) <= date_to_obj]
        except:
            pass
    
    if search:
        filtered_jobs = [
            j for j in filtered_jobs 
            if search in j.get('title', '').lower() 
            or search in j.get('description', '').lower()
            or search in j.get('company', '').lower()
        ]
    
    if job_type != 'all':
        filtered_jobs = [j for j in filtered_jobs if j.get('type') == job_type]
    
    return jsonify({
        "jobs": filtered_jobs,
        "count": len(filtered_jobs),
        "total": len(jobs_data)
    })

@app.route('/api/jobs/<int:job_id>')
def get_job(job_id):
    """Get a specific job by ID"""
    job = next((j for j in jobs_data if j['id'] == job_id), None)
    if job:
        return jsonify(job)
    return jsonify({"error": "Job not found"}), 404

@app.route('/api/stats')
def get_statistics():
    """Get statistics about jobs"""
    return jsonify(get_stats())

@app.route('/api/images/<path:filename>')
def serve_image(filename):
    """Serve job posting images"""
    try:
        if Path("screenshots") / filename:
            return send_from_directory("screenshots", filename)
        elif Path("extracted_images") / filename:
            return send_from_directory("extracted_images", filename)
    except:
        pass
    
    return jsonify({"error": "Image not found"}), 404

@app.route('/api/export')
def export_jobs():
    """Export all jobs as JSON"""
    return jsonify(jobs_data)

# ============================================================================
# WEBSOCKET EVENTS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    print(f"🔌 Client connected: {request.sid}")
    # Send current data to newly connected client
    emit('initial_data', {
        'jobs': jobs_data,
        'stats': get_stats(),
        'monitoring_status': monitoring_status
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    print(f"🔌 Client disconnected: {request.sid}")

@socketio.on('request_update')
def handle_update_request():
    """Client requests data update"""
    emit('jobs_updated', {
        'jobs': jobs_data,
        'stats': get_stats()
    })

# ============================================================================
# FILE WATCHER
# ============================================================================

def start_file_watcher():
    """Start watching jobs_data.json for changes"""
    event_handler = JobFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()
    print("👁 File watcher started")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize():
    """Initialize the application"""
    print("\n" + "="*70)
    print("WhatsApp IT Job Monitor - API Server")
    print("="*70 + "\n")
    
    # Create necessary directories
    Path("screenshots").mkdir(exist_ok=True)
    Path("extracted_images").mkdir(exist_ok=True)
    
    # Load existing jobs
    load_jobs()
    
    print(f"✓ API Server initialized")
    print(f"✓ Loaded {len(jobs_data)} jobs")
    
    # Start file watcher in separate thread
    watcher_thread = threading.Thread(target=start_file_watcher, daemon=True)
    watcher_thread.start()

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    initialize()
    
    print("\n" + "="*70)
    print("🚀 SERVER STARTING")
    print("="*70)
    print(f"\n📡 API Server: http://localhost:5000")
    print(f"🌐 Web Interface: http://localhost:5000")
    print(f"🔌 WebSocket: ws://localhost:5000")
    print(f"\n📚 API Endpoints:")
    print(f"   GET  /api/health              - Health check")
    print(f"   GET  /api/jobs                - Get all jobs")
    print(f"   GET  /api/jobs/<id>           - Get specific job")
    print(f"   GET  /api/stats               - Get statistics")
    print(f"   GET  /api/export              - Export jobs")
    print(f"   GET  /api/images/<filename>   - Get job images")
    print(f"\n💡 Tip: Open http://localhost:5000 in your browser")
    print(f"\nPress Ctrl+C to stop\n")
    
    # Run server with WebSocket support
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
