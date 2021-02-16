from pymongo import MongoClient
from copy import deepcopy
from ACC_Credentials import MONGO_LINK

MONGO_CLIENT = MongoClient(MONGO_LINK)
ACC_COLLECTION = MONGO_CLIENT.isda

class Driver():
    def __init__(self, name='', country='', driver_id='', results=[], points=0, team=''):
        self.name=name
        self.country=country
        self.steamid=driver_id
        self.results=results
        self.points=points
        self.team=team

    def to_json(self):
        self.populate_driver_data()
        return {
            'name': self.name,
            'country': str.lower(self.country),
            'results': self.results,
            'points': self.points,
            'team': self.team
        }

    def populate_driver_data(self):
        driver_data = ACC_COLLECTION.Drivers.find_one({'steam_guid': self.steamid})
        if driver_data is not None:
            self.name = driver_data['real_name']
            self.country = driver_data['country']
        else:
            self.name = 'Unknown Driver'
            self.country = 'un'

class Team():
    def __init__(self, name='', country='', car='', points=0):
        self.name = name
        self.country = country
        self.car = car
        self.points = points
    
    def to_json(self):
        return {
            'name': self.name,
            'country': self.country,
            'car': self.car,
            'points': self.points
        }

def sort_drivers_by_points(driver_list):
    driver_list.sort(key=lambda x: x.points, reverse=True)
    list_of_points = []
    last_point_checked = None
    last_list_index = -1

    # Grouping drivers by points
    for driver in driver_list:
        if driver.points != last_point_checked:
            list_of_points.append([driver])
            last_point_checked = driver.points
            last_list_index += 1
        else:
            list_of_points[last_list_index].append(driver)

    for point in list_of_points:
        if len(point) <= 1:
            continue
        point.sort(key=lambda x: x.results.count('DNF'), reverse=True)
        for pos in reversed(range(len(driver_list) + 1)):
            point.sort(key=lambda x: x.results.count(pos), reverse=True)
        point.sort(key=lambda x: x.results.count('DSQ'), reverse=True)

    return_list = []
    for point in list_of_points:
        for driver in point:
            return_list.append(driver)
    return return_list

def parse_season_results(race_list, car_entry_list):
    drivers_list = []
    default_results = [''] * len(race_list)
    for i in range(len(race_list)):
        if len(race_list[i]['results']['r']):
            default_results[i] = 'DNS'
    for i in range(len(race_list)):
        for entry in race_list[i]['results']['q']:
            # Checking if the driver exists in the list
            driver = next((dr for dr in drivers_list if dr.steamid == entry['drivers'][0]['steam_guid']), None)
            if driver is None:
                drivers_list.append(Driver(
                    driver_id=entry['drivers'][0]['steam_guid'],
                    results=deepcopy(default_results),
                    points=entry['points']
                ))
            else:
                driver.points += entry['points']
        position = 1
        for entry in race_list[i]['results']['r']:
            # Checking if the driver exists in the list
            driver = next((dr for dr in drivers_list if dr.steamid == entry['drivers'][0]['steam_guid']), None)
            driver_position = deepcopy(position)
            if entry['gap'] in ['DSQ', 'DNS', 'DNF']:
                driver_position = entry['gap']

            if driver is None:
                results = deepcopy(default_results)
                results[i] = deepcopy(driver_position)
                drivers_list.append(Driver(
                    driver_id=entry['drivers'][0]['steam_guid'],
                    results=deepcopy(results),
                    points=entry['points']
                ))
            else:
                driver.results[i] = deepcopy(driver_position)
                driver.points += entry['points']
            position += 1

    # Fetching list of teams in a season
    teams_list = []
    for car in car_entry_list:
        entry = ACC_COLLECTION.Cars.find_one({'id': car})
        if entry is not None:
            team = next((tm for tm in teams_list if tm.name == entry['team']), None)
            if team is None:
                teams_list.append(Team(name=entry['team'], car=entry['car_type']))
            driver = next((dr for dr in drivers_list if dr.steamid == entry['drivers'][0]), None)
            if driver is not None:
                driver.team = deepcopy(entry['team'])


    sorted_list = sort_drivers_by_points(drivers_list)
    driver_list = []
    for driver in sorted_list:
        driver_list.append(driver.to_json())
        team = next((tm for tm in teams_list if tm.name == driver.team), None)
        if team is not None:
            team.points += driver.points
            teams_list.sort(key=lambda x: x.points, reverse=True)

    team_list = []
    for team in teams_list:
        team_list.append(team.to_json())
    return driver_list, team_list
