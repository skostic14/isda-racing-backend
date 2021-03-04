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
            'real_name': str(str(request_dict['name'] + ' ' + str(request_dict['surname']))),
            'discord_id': request_dict['discordid']
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

@app.route("/get_upcoming_races/", methods=['GET'])
@cross_origin()
def get_upcoming_races():
    upcoming_races = ACC_COLLECTION.Races.find({'date': {'$gte': get_date_today()}})
    race_list = {'races': []}
    for race in upcoming_races:
        track = ACC_COLLECTION.Venues.find_one({'id': race['track']})
        race_list['races'].append({
            'id': race['id'],
            'name': race['friendly_name'],
            'track': track['friendly_name'],
            'country': track['country'],
            'date': race['date'],
            'start_time': race['race_start_time'],
            'sessions': race['sessions']
        })
    race_list['races'].sort(key=lambda x: x['date'])
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

@app.route("/get_active_drivers", methods=['GET'])
@cross_origin()
def get_active_drivers():
    active_drivers = ACC_COLLECTION.Drivers.find({'status': {'$ne': 'blocked'}})
    drivers_list = []
    for driver in active_drivers:
        if driver == '':
            break
        drivers_list.append({
            'real_name': driver['real_name'],
            'country': driver['country']
        })
    return json.dumps({'drivers': drivers_list}), 200, {'ContentType':'application/json'}

@app.route("/get_car_options", methods=['GET'])
@cross_origin()
def get_car_options():
    season_id = request.args.get('season')
    season = ACC_COLLECTION.Seasons.find_one({'id': season_id})
    if season is not None:
        car_list = []
        for car_class in season['classes']:
            simulator = season['simulator']
            cars_in_class = ACC_COLLECTION.Car_Types.find({'$and': [{'class': car_class}, {str('game_ids.' + simulator): {'$exists': True}}]})
            for car in cars_in_class:
                car_list.append({
                    'friendly_name': str(car['brand'] + ' ' + car['model_name']),
                    'id': car['id'],
                    'class': car['class']
                })
        return json.dumps({'cars': car_list}), 200, {'ContentType':'application/json'}
    return json.dumps({'message': 'Season not found!'}), 500, {'ContentType':'application/json'}

@app.route("/team_signup", methods=['POST'])
@cross_origin()
def team_signup():
    request_dict = request.get_json()

    season_id = request_dict['season']
    team_name = request_dict['teamname']
    car_number = request_dict['car_number']
    car_type = request_dict['car']
    pin_code = request_dict['pin']

    season = ACC_COLLECTION.Seasons.find_one({'id': season_id})
    registered_entries = ACC_COLLECTION.Cars.find({'id': {'$in': season['entries']}})
    driver_list = []
    driver_id_list = []
    for driver_name in request_dict['drivers']:
        if driver_name == '':
            break
        driver = ACC_COLLECTION.Drivers.find_one({'real_name': driver_name})
        driver_list.append({'name': driver_name, 'steam_id': driver['steam_guid'], 'category': 'pro'})
        driver_id_list.append(driver['steam_guid'])

    # Check for collisions with other teams
    for entry in registered_entries:
        # Check if the car number is already registered
        if car_number == entry['entry_number']:
            return json.dumps({'message': 'Car number already in use'}), 500, {'ContentType':'application/json'}

        # Check if drivers exist in other entries of the season
        for driver in driver_list:
            if driver['steam_id'] in entry['drivers']:
                return json.dumps({'message': str('Driver ' + driver['name'] + ' is in another team')}), 500, {'ContentType':'application/json'}

    entry_id = str(team_name.replace(' ', '') + str(car_number)).lower()
    
    car_entry_dict = {
        'id': entry_id,
        'team': team_name,
        'drivers': driver_id_list,
        'entry_number': car_number,
        'car_type': car_type,
        'bop': {
            'ballast': 0,
            'restrictor': 0
        },
        'pin': pin_code
    }
    ACC_COLLECTION.Cars.insert_one(car_entry_dict)

    team_entry_dict = {
        'team_name': team_name,
        'drivers': driver_list,
        'category': 'pro',
        'pin': pin_code
    }
    ACC_COLLECTION.Teams.insert_one(team_entry_dict)

    query = {'id': season_id}
    post = {'$push': {'entries': entry_id}}
    ACC_COLLECTION.Seasons.update_one(query, post)
    return json.dumps({'message': 'Sign-up successful!'}), 200, {'ContentType':'application/json'}

@app.route("/team_update", methods=['POST'])
@cross_origin()
def team_update():
    request_dict = request.get_json()
    season_id = request_dict['season']
    team_id = request_dict['team_id']
    team_name = request_dict['teamname']
    car_number = request_dict['car_number']
    car_type = request_dict['car']
    pin_code = request_dict['pin']

    # Verify PIN Code
    entry = ACC_COLLECTION.Cars.find_one({'id': team_id, 'pin': pin_code})
    if entry is None:
        return json.dumps({'message': 'Incorrect PIN provided'}), 500, {'ContentType':'application/json'}

    season = ACC_COLLECTION.Seasons.find_one({'id': season_id})
    registered_entries = ACC_COLLECTION.Cars.find({'id': {'$in': season['entries']}})
    driver_list = []
    driver_id_list = []
    for driver_name in request_dict['drivers']:
        if driver_name == '':
            break
        driver = ACC_COLLECTION.Drivers.find_one({'real_name': driver_name})
        driver_list.append({'name': driver_name, 'steam_id': driver['steam_guid'], 'category': 'pro'})
        driver_id_list.append(driver['steam_guid'])

    # Check for collisions with other teams
    for entry in registered_entries:
        if entry['id'] == team_id:
            continue
        # Check if the car number is already registered
        if car_number == entry['entry_number']:
            return json.dumps({'message': 'Car number already in use'}), 500, {'ContentType':'application/json'}

        # Check if drivers exist in other entries of the season
        for driver in driver_list:
            if driver['steam_id'] in entry['drivers']:
                return json.dumps({'message': str('Driver ' + driver['name'] + ' is in another team')}), 500, {'ContentType':'application/json'}
    
    car_entry_dict = {
        'id': team_id,
        'team': team_name,
        'drivers': driver_id_list,
        'entry_number': car_number,
        'car_type': car_type,
        'bop': {
            'ballast': 0,
            'restrictor': 0
        },
        'pin': pin_code
    }
    query = {'id': team_id}
    post = {'$set': car_entry_dict}
    ACC_COLLECTION.Cars.update_one(query, post)
    return json.dumps({'message': 'Update successful!'}), 200, {'ContentType':'application/json'}

@app.route("/get_registered_teams", methods=['GET'])
@cross_origin()
def get_registered_teams():
    season_id = request.args.get('season')
    season = ACC_COLLECTION.Seasons.find_one({'id': season_id})
    if season is not None:
        registered_entries = ACC_COLLECTION.Cars.find({'id': {'$in': season['entries']}})
        team_list = []
        for entry in registered_entries:
            driver_list = []
            for steam_id in entry['drivers']:
                driver = ACC_COLLECTION.Drivers.find_one({'steam_guid': steam_id})
                driver_list.append({
                    'name': driver['real_name'],
                    'country': driver['country']
                })
            car = ACC_COLLECTION.Car_Types.find_one({'id': entry['car_type']})
            team_list.append({
                'id': entry['id'],
                'team_name': entry['team'],
                'car_id': entry['car_type'],
                'car_name': str(car['brand'] + ' ' + car['model_name']),
                'entry_number': entry['entry_number'],
                'drivers': driver_list
            })
        return json.dumps({'teams': team_list}), 200, {'ContentType':'application/json'}
    return json.dumps({'message': 'Season not found!'}), 500, {'ContentType':'application/json'}

if __name__ == '__main__':
    print('Server started')
    # Use this in local environment
    #app.run(host='0.0.0.0', port=3010)
    print('Server closed')
