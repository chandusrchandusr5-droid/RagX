from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        data = {
            "total_chunks": 3,
            "quality_metrics": {
                "text_extraction_completeness": 96.5,
                "chunk_diversity_index": 92.0,
                "contradiction_free_rate": 100.0,
                "overall_health_score": 95.8
            },
            "chunk_issues": []
        }
        self.wfile.write(json.dumps(data).encode('utf-8'))
        return
