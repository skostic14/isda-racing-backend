import http.server
import json
from urllib.parse import urlparse, unquote
from pymongo import MongoClient
import requests

MONGO_LINK = 'mongodb://localhost:27017/'
MONGO_CLIENT = MongoClient(MONGO_LINK)
ACC_COLLECTION = MONGO_CLIENT.test

class RequestHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        query = urlparse(unquote(self.path)).query
        query_parameters = dict(parameters.split('=') for parameters in query.split('&'))
        race = query_parameters['race_id']
        session = query_parameters['session']
        race_json = ACC_COLLECTION.Races.find_one({'id': race})
        results_list = []
        if session in race_json['results']:
            results_list = race_json['results'][session]
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(results_list).encode(encoding='utf-8'))

if __name__ == '__main__':
    HOST, PORT = '0.0.0.0', 3010
    ServerClass = http.server.ThreadingHTTPServer
    HTTP_SERVER = ServerClass((HOST, PORT), RequestHandler)
    print('Server started')
    try:
        HTTP_SERVER.serve_forever()
    except:
        pass
    HTTP_SERVER.server_close()
    print('Server closed')