from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        data = {
            "total_documents": 1,
            "documents": [
                {
                    "document_id": "doc-vtu-001",
                    "document_name": "2ND SEM RESULT.pdf",
                    "original_filename": "2ND SEM RESULT.pdf",
                    "upload_date": "2024-08-16 10:00:00",
                    "file_size": "40.6 KB",
                    "total_pages": 1,
                    "total_chunks": 3,
                    "status": "ACTIVE"
                }
            ]
        }
        self.wfile.write(json.dumps(data).encode('utf-8'))
        return
