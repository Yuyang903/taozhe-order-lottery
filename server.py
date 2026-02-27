import http.server
import socketserver
import json
import os
from datetime import datetime

from urllib.parse import urlparse

PORT = 8000

# File paths
ORDERS_FILE = 'orders.json'
WINNERS_FILE = 'winners.json'

class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True

class LotteryHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to all responses
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        # Add Cache-Control to prevent caching issues during development
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        super().end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/get_orders':
            self.send_json_file(ORDERS_FILE, [])
        elif path == '/api/get_winners':
            self.send_json_file(WINNERS_FILE, [])
        else:
            super().do_GET()

    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/api/save_orders':
            # Overwrite orders.json with new list
            self.handle_save_json(ORDERS_FILE)
        
        elif path == '/api/append_orders':
            # Append to orders.json
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                new_orders = json.loads(post_data.decode('utf-8'))
                
                if not isinstance(new_orders, list):
                    raise ValueError("Data must be a list")

                current_orders = self.read_json_file(ORDERS_FILE, [])
                
                # Append and remove duplicates (optional, but good practice)
                # For large datasets, set might be better, but list preserves order
                # Let's just append for now to be fast, or use set to de-dupe
                
                # Simple append
                current_orders.extend(new_orders)
                
                # Write back
                self.write_json_file(ORDERS_FILE, current_orders)
                
                self.send_response_json({'status': 'success', 'count': len(current_orders), 'added': len(new_orders)})
                print(f"Appended {len(new_orders)} orders.")
                
            except Exception as e:
                self.send_error_json(str(e))

        elif path == '/api/record_winner':
            # Record a winner
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                winner_data = json.loads(post_data.decode('utf-8'))
                
                # Expecting {"no": "...", "time": "..."}
                if 'no' not in winner_data:
                    raise ValueError("Missing 'no' field")

                winners = self.read_json_file(WINNERS_FILE, [])
                
                # Check if already exists
                if not any(w['no'] == winner_data['no'] for w in winners):
                    winners.append(winner_data)
                    self.write_json_file(WINNERS_FILE, winners)
                    print(f"Recorded winner: {winner_data['no']}")
                
                self.send_response_json({'status': 'success'})
                
            except Exception as e:
                self.send_error_json(str(e))
                
        elif path == '/api/reset_winners':
             # Clear winners
            try:
                self.write_json_file(WINNERS_FILE, [])
                self.send_response_json({'status': 'success'})
                print("Winners reset.")
            except Exception as e:
                 self.send_error_json(str(e))

        else:
            self.send_error(404, "API endpoint not found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    # --- Helpers ---
    def read_json_file(self, filepath, default):
        if not os.path.exists(filepath):
            return default
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default

    def write_json_file(self, filepath, data):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def send_json_file(self, filepath, default):
        data = self.read_json_file(filepath, default)
        self.send_response_json(data)

    def send_response_json(self, data):
        response_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-Length', str(len(response_data)))
        self.end_headers()
        self.wfile.write(response_data)

    def send_error_json(self, message, code=500):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'error', 'message': message}, ensure_ascii=False).encode('utf-8'))

    def handle_save_json(self, filepath):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            if not isinstance(data, list):
                raise ValueError("Data must be a list")

            self.write_json_file(filepath, data)
            self.send_response_json({'status': 'success', 'count': len(data)})
            print(f"Saved {len(data)} items to {filepath}")
        except Exception as e:
            self.send_error_json(str(e))

print(f"Starting local server at http://localhost:{PORT}")
print("--------------------------------------------------")
print(f"Admin Dashboard: http://localhost:{PORT}/admin.html")
print(f"Lottery Page:    http://localhost:{PORT}/lottery.html")
print("--------------------------------------------------")
print("Press Ctrl+C to stop the server.")

# Allow address reuse to avoid "Address already in use" errors
socketserver.TCPServer.allow_reuse_address = True

try:
    # Use ThreadingHTTPServer instead of TCPServer for better concurrency
    with ThreadingHTTPServer(("", PORT), LotteryHandler) as httpd:
        httpd.serve_forever()
except KeyboardInterrupt:
    print("\nServer stopped.")
