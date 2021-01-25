import sys
import json
import datetime
from pymongo import MongoClient
from ACC_Backend_Utils import get_time_from_milliseconds
from ACC_Credentials import MONGO_LINK

MONGO_CLIENT = MongoClient(MONGO_LINK)
ACC_COLLECTION = MONGO_CLIENT.isda

class Driver():
    def __init__(self, json_data):
        self.name = str(json_data['firstName'] + ' ' + json_data['lastName'])
        self.steam_id = json_data['playerId']
        self.driving_time = 0
        self.penalties = []

    def to_dict(self):
        print(self.penalties)
        return {
            'name': self.name,
            'steam_guid': self.steam_id,
            'driving_time': get_time_from_milliseconds(self.driving_time),
            'penalties': self.penalties
        }

class CarResult():
    def __init__(self, json_data):
        self.car_id = json_data['car']['carId']
        self.race_number = json_data['car']['raceNumber']
        self.car_model = json_data['car']['carModel']
        self.drivers = []
        for driver_index in range(len(json_data['car']['drivers'])):
            new_driver = Driver(json_data['car']['drivers'][driver_index])
            if driver_index < len(json_data['driverTotalTimes']):
                #new_driver.driving_time = get_time_from_milliseconds(json_data['driverTotalTimes'][driver_index])
                new_driver.driving_time = int(json_data['driverTotalTimes'][driver_index])
            self.drivers.append(new_driver)
        #self.fastest_lap = get_time_from_milliseconds(int(json_data['timing']['bestLap']))
        #self.total_time = get_time_from_milliseconds(int(json_data['timing']['totalTime']))
        self.fastest_lap = int(json_data['timing']['bestLap'])
        self.total_time = int(json_data['timing']['totalTime'])
        self.lap_count = int(json_data['timing']['lapCount'])
        self.gap = 0

    def to_json(self):
        drivers_json = []
        for driver in self.drivers:
            drivers_json.append(driver.to_dict())
        return {
            'race_number': self.race_number,
            'drivers': drivers_json,
            'fastest_lap': get_time_from_milliseconds(self.fastest_lap),
            'total_time': get_time_from_milliseconds(self.total_time),
            'gap': get_time_from_milliseconds(self.gap),
            'laps': self.lap_count
        }

class Session():
    def __init__(self, json_data):
        self.session_type = json_data['sessionType'].lower()
        self.car_results = []
        for car in json_data['sessionResult']['leaderBoardLines']:
            car_result = CarResult(car)
            for penalty in json_data['penalties']:
                if penalty['carId'] == car_result.car_id and penalty['penalty'] != 'None':
                    print('found penalty for', penalty['carId'], penalty['penalty'])
                    car_result.drivers[penalty['driverIndex']].penalties.append({
                        'penalty': penalty['penalty'],
                        'reason': penalty['reason'],
                        'lap': penalty['violationInLap']
                    })
                    print(car_result.drivers[penalty['driverIndex']].penalties)
            self.car_results.append(car_result)
        self.fill_gaps()

    def fill_gaps(self):
        if self.session_type == 'r':
            time_interval = self.car_results[0].total_time
            for car in self.car_results:
                car.gap = car.total_time - time_interval
                time_interval = car.total_time
        else:
            print(self.session_type)
            time_interval = self.car_results[0].fastest_lap
            for car in self.car_results:
                car.gap = car.fastest_lap - time_interval
                time_interval = car.fastest_lap

def find_sessions_by_date(date):
    query: {'date': date}
    return ACC_COLLECTION.Races.find_one(query)

def upload_session(session, season_id, event_id):
    query = {'id': event_id}
    season = ACC_COLLECTION.Seasons.find_one({'id': season_id})
    points_array = [0] * len(session.car_results)
    if session.session_type in season['rules']['points']:
        session_points = season['rules']['points'][session.session_type]
        for i in range(len(session_points)):
            if i == len(points_array):
                break
            points_array[i] = session_points[i]

    session_data = []
    position_counter = 0
    for car in session.car_results:
        car_dict = car.to_json()
        car_dict['points'] = points_array[position_counter]
        position_counter += 1
        # TODO : add logic for DNF
        session_data.append(car_dict)

    post = {'$set': {str('results.' + session.session_type): session_data}}
    ACC_COLLECTION.Races.update_one(query, post)

if __name__ == '__main__':
    session_file = input('Enter .json file_name: ')
    print(session_file)

    # NOTE: 'rt' argument is required because of results encoding
    #session_data = json.load(open(session_file, 'rt', encoding='utf_16_le'))
    session_data = json.load(open(session_file, 'rt', encoding='utf-8'), strict=False)
    print(session_data['serverName'])
    session = Session(session_data)
    # print drivers
    for car in session.car_results:
        for driver in car.drivers:
            print(driver.name)
    no_results_query = {
        #session.session_type: '{$exists: true, $size: 0}'
        'results.r': {'$exists': True, '$size': 0}#, $size: 0}'
    }
    query = ACC_COLLECTION.Races.find(no_results_query)
    upload_session(session, 'ACC_Pcup_S0', 'ACC_Friendly_BritishVsGerman_Zandvoort')
    for session in query:
        print(session['id'])