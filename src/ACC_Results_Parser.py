import sys
import json
import datetime
from pymongo import MongoClient
from copy import deepcopy
from ACC_Backend_Utils import get_time_from_milliseconds
from ACC_Credentials import MONGO_LINK

MONGO_CLIENT = MongoClient(MONGO_LINK)
ACC_COLLECTION = MONGO_CLIENT.isda

class Driver():
    def __init__(self, json_data):
        self.name = 'Unknown driver'
        self.steam_id = json_data['playerId']
        self.driving_time = 0
        self.penalties = []

    def populate_driver_data(self):
        driver = ACC_COLLECTION.Drivers.find_one({'steam_guid': self.steam_id})
        if driver is not None:
            self.name = driver['real_name']

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
        if json_data['car']['cupCategory'] == 0:
            self.split = 'pro'
        elif json_data['car']['cupCategory'] == 1:
            self.split = 'silver'
        else:
            self.split = 'am'
        self.gap = 0

    def to_json(self):
        drivers_json = []
        for driver in self.drivers:
            driver.populate_driver_data()
            drivers_json.append(driver.to_dict())
        return {
            'race_number': self.race_number,
            'drivers': drivers_json,
            'class': self.split,
            'fastest_lap': get_time_from_milliseconds(self.fastest_lap),
            'total_time': get_time_from_milliseconds(self.total_time),
            'gap': self.gap,
            'laps': self.lap_count
        }

class Session():
    def __init__(self, json_data, is_multiclass):
        self.session_type = json_data['sessionType'].lower()
        self.overall_results = []
        self.pro_results = []
        self.silver_results = []
        self.am_results = []
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
            self.overall_results.append(car_result)
            if is_multiclass:
                if car_result.split == 'pro':
                    self.pro_results.append(deepcopy(car_result))
                elif car_result.split == 'silver':
                    self.silver_results.append(deepcopy(car_result))
                elif car_result.split == 'am':
                    self.am_results.append(deepcopy(car_result))
        self.fill_gaps(self.overall_results)
        if is_multiclass:
            if len(self.pro_results):
                self.fill_gaps(self.pro_results)
            if len(self.silver_results):
                self.fill_gaps(self.silver_results)
            if len(self.am_results):
                self.fill_gaps(self.am_results)

    def fill_gaps(self, results):
        if self.session_type == 'r':
            time_interval = results[0].total_time
            lead_lap_count = results[0].lap_count
            prev_lap_count = results[0].lap_count
            for car in results:
                if car.lap_count < lead_lap_count * 0.75:
                    car.gap = "DNF"
                elif prev_lap_count != car.lap_count:
                    car.gap = "+{:d} LAP".format(lead_lap_count - car.lap_count)
                else:
                    car.gap = get_time_from_milliseconds(car.total_time - time_interval)
                time_interval = car.total_time
                prev_lap_count = car.lap_count
        else:
            print(self.session_type)
            time_interval = results[0].fastest_lap
            for car in results:
                car.gap = get_time_from_milliseconds(car.fastest_lap - time_interval)
                time_interval = car.fastest_lap

def find_sessions_by_date(date):
    query: {'date': date}
    return ACC_COLLECTION.Races.find_one(query)

def upload_session(session, season_id, event_id, is_multiclass):
    query = {'id': event_id}
    season = ACC_COLLECTION.Seasons.find_one({'id': season_id})
    points_array = [0] * len(session.overall_results)
    if session.session_type in season['rules']['points']:
        session_points = season['rules']['points'][session.session_type]
        for i in range(len(session_points)):
            if i == len(points_array):
                break
            points_array[i] = session_points[i]

    overall_results = []
    position_counter = 0
    for car in session.overall_results:
        car_dict = car.to_json()
        if not is_multiclass:
            car_dict['points'] = points_array[position_counter]
        else:
            car_dict['points'] = 0
        position_counter += 1
        overall_results.append(car_dict)
    
    results_dict = {
        str('results.' + session.session_type + '.overall'): overall_results
    }

    if is_multiclass:
        if len(session.pro_results):
            pro_results = []
            position_counter = 0
            for car in session.pro_results:
                car_dict = car.to_json()
                car_dict['points'] = points_array[position_counter]
                position_counter += 1
                pro_results.append(car_dict)
            results_dict[str('results.' + session.session_type + '.pro')] = pro_results

        if len(session.silver_results):
            silver_results = []
            position_counter = 0
            for car in session.silver_results:
                car_dict = car.to_json()
                car_dict['points'] = points_array[position_counter]
                position_counter += 1
                silver_results.append(car_dict)
            results_dict[str('results.' + session.session_type + '.silver')] = silver_results

        if len(session.am_results):
            am_results = []
            position_counter = 0
            for car in session.am_results:
                car_dict = car.to_json()
                car_dict['points'] = points_array[position_counter]
                position_counter += 1
                am_results.append(car_dict)
            results_dict[str('results.' + session.session_type + '.am')] = am_results

    post = {'$set': results_dict}
    ACC_COLLECTION.Races.update_one(query, post)

if __name__ == '__main__':
    session_file = input('Enter .json file_name: ')
    print(session_file)
    season_id = input('Enter season ID: ')
    race_id = input('Enter race ID: ')
    is_multiclass = int(input('Race is multiclass? [0 - no, 1 - yes]: '))

    # NOTE: 'rt' argument is required because of results encoding
    session_data = json.load(open(session_file, 'rt', encoding='utf_16_le'))
    #session_data = json.load(open(session_file, 'rt', encoding='utf-8'), strict=False)
    print(session_data['serverName'])
    session = Session(session_data, is_multiclass)
    # print drivers
    for car in session.overall_results:
        for driver in car.drivers:
            print(driver.name)
    no_results_query = {
        #session.session_type: '{$exists: true, $size: 0}'
        'results.r': {'$exists': True, '$size': 0}#, $size: 0}'
    }
    query = ACC_COLLECTION.Races.find(no_results_query)
    upload_session(session, season_id, race_id, is_multiclass)
    for session in query:
        print(session['id'])