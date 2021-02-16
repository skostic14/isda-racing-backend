import http.server
import json
from urllib.parse import urlparse, unquote
from pymongo import MongoClient
from flask import Flask, request
from flask_cors import CORS, cross_origin
from ACC_Backend_Utils import get_date_today
from ACC_Credentials import MONGO_LINK
from Standings import parse_season_results
import requests

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
        return json.dumps(race_result), 200, {'ContentType':'application/json'}
    return json.dumps({'message': 'Session not found!'}), 500, {'ContentType':'application/json'}

@app.route("/get_available_race_results/", methods=['GET'])
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

@app.route("/get_available_seasons/", methods=['GET'])
@cross_origin()
def get_available_seasons():
    seasons = ACC_COLLECTION.Seasons.find({})
    season_list = {'seasons': []}
    for season in seasons:
        season_list['seasons'].append({
            'id': season['id'],
            'name': season['friendly_name'],
            'description': season['description'],
            'banner_link': season['banner_link'],
            'simulator': season['simulator'],
            'classes': season['classes']
        })
    return json.dumps(season_list), 200, {'ContentType': 'application/json'}

@app.route("/update_season_standings", methods=['GET'])
@cross_origin()
def update_season_standings():
    season_id = request.args.get('id')
    season = ACC_COLLECTION.Seasons.find_one({'id': season_id})
    if season is not None:
        race_list = []
        race_abbreviations = []
        for race_id in season['events']:
            race = ACC_COLLECTION.Races.find_one({'id': race_id})
            race_list.append(race)
            race_abbreviations.append(str.upper(race['track'][0:3]))
        driver_standings, team_standings = parse_season_results(race_list, season['entries'])
        ACC_COLLECTION.Seasons.update_one({'id': season_id}, {'$set': {
            'standings': {
                'races': race_abbreviations, 
                'driver_standings': driver_standings,
                'team_standings': team_standings
            }}})
        return json.dumps({'driver_standings': driver_standings, 'team_standings': team_standings, 'races': race_abbreviations}), 200, {'ContentType':'application/json'}
    return json.dumps({'message': 'Season not found!'}), 500, {'ContentType':'application/json'}

@app.route("/get_season_standings", methods=['GET'])
@cross_origin()
def get_season_standings():
    season_id = request.args.get('id')
    season = ACC_COLLECTION.Seasons.find_one({'id': season_id})
    if season is not None:
        return json.dumps(season['standings']), 200, {'ContentType':'application/json'}
    return json.dumps({'message': 'Season not found!'}), 500, {'ContentType':'application/json'}

if __name__ == '__main__':
    print('Server started')
    # Use this in local environment
    # app.run(host='0.0.0.0', port=3010)
    print('Server closed')