import http.server
import json
from urllib.parse import urlparse, unquote
from pymongo import MongoClient
from flask import Flask, request
from flask_cors import CORS, cross_origin
from ACC_Backend_Utils import get_date_today
import requests

MONGO_LINK = 'mongodb://<HIDDEN>/?authSource=admin'
MONGO_CLIENT = MongoClient(MONGO_LINK)
ACC_COLLECTION = MONGO_CLIENT.isda

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

@app.route("/signup/", methods=['POST'])
@cross_origin()
def post_signup():
    request_dict = request.get_json()

    existing_driver = ACC_COLLECTION.Drivers.find_one({'steam_guid': str('S' + str(request_dict['steamid']))})
    if existing_driver is None:
        new_driver = {
            'steam_guid': str('S' + str(request_dict['steamid'])),
            'country': str(request_dict['country']),
            'birth_date': '1970-01-01',
            'display_name': [str(str(request_dict['name']) + ' ' + str(request_dict['nickname'] + ' ' + str(request_dict['surname'])))],
            'real_name': str(str(request_dict['name'] + ' ' + str(request_dict['surname'])))
        }
        ACC_COLLECTION.Drivers.insert_one(new_driver)
        return json.dumps({'message': 'Sign-up successful!'}), 200, {'ContentType':'application/json'}

    return json.dumps({'message': 'Driver already exists!'}), 400, {'ContentType':'application/json'}

@app.route("/get_race_results", methods=['GET'])
@cross_origin()
def get_race_results():
    race = request.args.get('id')
    session = request.args.get('session')
    race_json = ACC_COLLECTION.Races.find_one({'id': race})
    if session in race_json['results']:
        race_result = {
            'race_data': {
                'date': race_json['date'],
                'start_time': race_json['race_start_time']
            },
            'results': race_json['results'][session]
        }
        return json.dumps(race_result, 200, {'ContentType':'application/json'})
    return json.dumps({'message': 'Session not found!'}), 500, {'ContentType':'application/json'}

@app.route("/get_available_race_results", methods=['GET'])
@cross_origin()
def get_available_race_results():
    past_races = ACC_COLLECTION.Races.find({'date': {'$lte': get_date_today()}})
    race_list = {'races': []}
    for race in past_races:
        if 'r' in race['results'] and len(race['results']['r']) > 0: 
            race_list['races'].append({
                'id': race['id'],
                'name': race['friendly_name']
            })
    return json.dumps(race_list), 200, {'ContentType': 'application/json'}

if __name__ == '__main__':
    print('Server started')
    #app.run(host='0.0.0.0', port=3010, ssl_context=('cert.pem', 'key.pem'))
    print('Server closed')
