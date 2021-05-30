from pymongo import MongoClient
from copy import deepcopy
from ACC_Credentials import MONGO_LINK

MONGO_CLIENT = MongoClient(MONGO_LINK)
ACC_COLLECTION = MONGO_CLIENT.isda

class Driver():
    def __init__(self, name='', country='', driver_id=[], results=[], points=0, team=''):
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
        for driver_id in self.steamid:
            driver_data = ACC_COLLECTION.Drivers.find_one({'steam_guid': driver_id})
            if driver_data is not None:
                self.name += driver_data['real_name']
                self.country += driver_data['country']
            else:
                self.name += 'Unknown Driver'
                self.country += 'un'
            self.name += ' / '
            self.country += ' / '
        self.name = self.name[0:-3]
        self.country = self.country[0:-3]

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
        point.sort(key=lambda x: x.results.count('DSQ'), reverse=False)

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
            # Checking if the drivers exist in the list
            drivers_ids = [driver['steam_guid'] for driver in entry['drivers']]
            drivers = next((dr for dr in drivers_list if dr.steamid == drivers_ids), None)
            if drivers is None:
                drivers_list.append(Driver(
                    driver_ids=drivers_ids,
                    results=deepcopy(default_results),
                    points=entry['points']
                ))
            else:
                drivers.points += entry['points']
        position = 1
        for entry in race_list[i]['results']['r']:
            # Checking if the driver exists in the list
            drivers_ids = [driver['steam_guid'] for driver in entry['drivers']]
            drivers = next((dr for dr in drivers_list if dr.steamid == drivers_ids), None)
            driver_position = deepcopy(position)
            if entry['gap'] in ['DSQ', 'DNS', 'DNF']:
                driver_position = entry['gap']

            if drivers is None:
                results = deepcopy(default_results)
                results[i] = deepcopy(driver_position)
                drivers_list.append(Driver(
                    driver_id=drivers_ids,
                    results=deepcopy(results),
                    points=entry['points']
                ))
            else:
                drivers.results[i] = deepcopy(driver_position)
                drivers.points += entry['points']
            position += 1

    # Fetching list of teams in a season
    teams_list = []
    for car in car_entry_list:
        entry = ACC_COLLECTION.Cars.find_one({'id': car})
        if entry is not None:
            team = next((tm for tm in teams_list if tm.name == entry['team']), None)
            if team is None:
                teams_list.append(Team(name=entry['team'], car=entry['car_type']))
            drivers_ids = [driver['steam_guid'] for driver in entry['drivers']]
            drivers = next((dr for dr in drivers_list if dr.steamid == drivers_ids), None)
            if drivers is not None:
                drivers.team = deepcopy(entry['team'])


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

def parse_season_results_multiclass(race_list, car_entry_list):
    drivers_list_am = []
    drivers_list_silver = []
    drivers_list_pro = []
    default_results = [''] * len(race_list)
    for i in range(len(race_list)):
        if len(race_list[i]['results']['r']['overall']):
            default_results[i] = 'DNS'
    for i in range(len(race_list)):
        for entry in race_list[i]['results']['q']['am']:
            # Checking if the driver exists in the list
            drivers_ids = [driver['steam_guid'] for driver in entry['drivers']]
            drivers = next((dr for dr in drivers_list_am if dr.steamid == drivers_ids), None)
            if drivers is None:
                drivers_list_am.append(Driver(
                    driver_id=drivers_ids,
                    results=deepcopy(default_results),
                    points=entry['points']
                ))
            else:
                drivers.points += entry['points']

        for entry in race_list[i]['results']['q']['pro']:
            # Checking if the driver exists in the list
            drivers_ids = [driver['steam_guid'] for driver in entry['drivers']]
            drivers = next((dr for dr in drivers_list_pro if dr.steamid == drivers_ids), None)
            if drivers is None:
                drivers_list_pro.append(Driver(
                    driver_id=drivers_ids,
                    results=deepcopy(default_results),
                    points=entry['points']
                ))
            else:
                drivers.points += entry['points']

        for entry in race_list[i]['results']['q']['silver']:
            # Checking if the driver exists in the list
            drivers_ids = [driver['steam_guid'] for driver in entry['drivers']]
            drivers = next((dr for dr in drivers_list_silver if dr.steamid == drivers_ids), None)
            if drivers is None:
                drivers_list_silver.append(Driver(
                    driver_id=drivers_ids,
                    results=deepcopy(default_results),
                    points=entry['points']
                ))
            else:
                drivers.points += entry['points']

        position = 1
        for entry in race_list[i]['results']['r']['am']:
            # Checking if the driver exists in the list
            drivers_ids = [driver['steam_guid'] for driver in entry['drivers']]
            drivers = next((dr for dr in drivers_list_am if dr.steamid == drivers_ids), None)
            driver_position = deepcopy(position)
            if entry['gap'] in ['DSQ', 'DNS', 'DNF']:
                driver_position = entry['gap']

            if drivers is None:
                results = deepcopy(default_results)
                results[i] = deepcopy(driver_position)
                drivers_list_am.append(Driver(
                    driver_id=drivers_ids,
                    results=deepcopy(results),
                    points=entry['points']
                ))
            else:
                drivers.results[i] = deepcopy(driver_position)
                drivers.points += entry['points']
            position += 1
        
        position = 1
        for entry in race_list[i]['results']['r']['pro']:
            # Checking if the driver exists in the list
            drivers_ids = [driver['steam_guid'] for driver in entry['drivers']]
            drivers = next((dr for dr in drivers_list_pro if dr.steamid == drivers_ids), None)
            driver_position = deepcopy(position)
            if entry['gap'] in ['DSQ', 'DNS', 'DNF']:
                driver_position = entry['gap']

            if drivers is None:
                results = deepcopy(default_results)
                results[i] = deepcopy(driver_position)
                drivers_list_pro.append(Driver(
                    driver_id=drivers_ids,
                    results=deepcopy(results),
                    points=entry['points']
                ))
            else:
                drivers.results[i] = deepcopy(driver_position)
                drivers.points += entry['points']
            position += 1

        position = 1
        for entry in race_list[i]['results']['r']['silver']:
            # Checking if the driver exists in the list
            drivers_ids = [driver['steam_guid'] for driver in entry['drivers']]
            drivers = next((dr for dr in drivers_list_silver if dr.steamid == drivers_ids), None)
            driver_position = deepcopy(position)
            if entry['gap'] in ['DSQ', 'DNS', 'DNF']:
                driver_position = entry['gap']

            if drivers is None:
                results = deepcopy(default_results)
                results[i] = deepcopy(driver_position)
                drivers_list_silver.append(Driver(
                    driver_id=drivers_ids,
                    results=deepcopy(results),
                    points=entry['points']
                ))
            else:
                drivers.results[i] = deepcopy(driver_position)
                drivers.points += entry['points']
            position += 1

    # Fetching list of teams in a season
    teams_list = []
    for car in car_entry_list:
        entry = ACC_COLLECTION.Cars.find_one({'id': car})
        if entry is not None:
            team = next((tm for tm in teams_list if tm.name == entry['team']), None)
            if team is None:
                teams_list.append(Team(name=entry['team'], car=entry['car_type']))
            driver_am = next((dr for dr in drivers_list_am if dr.steamid == entry['drivers']), None)
            if driver_am is not None:
                driver_am.team = deepcopy(entry['team'])
                continue
            driver_pro = next((dr for dr in drivers_list_pro if dr.steamid == entry['drivers']), None)
            if driver_pro is not None:
                driver_pro.team = deepcopy(entry['team'])
                continue
            driver_silver = next((dr for dr in drivers_list_silver if dr.steamid == entry['drivers']), None)
            if driver_silver is not None:
                driver_silver.team = deepcopy(entry['team'])
                continue

    sorted_list_am = sort_drivers_by_points(drivers_list_am)
    drivers_list_am = []
    teams_list_am = []
    for driver in sorted_list_am:
        drivers_list_am.append(driver.to_json())
        team_am = next((tm for tm in teams_list_am if tm.name == driver.team), None)
        if team_am is None:
            team = next((tm for tm in teams_list if tm.name == driver.team), None)
            if team is not None:
                team.points += driver.points
                teams_list_am.append(deepcopy(team))
        else:
            team_am.points += driver.points
            teams_list_am.sort(key=lambda x: x.points, reverse=True)

    sorted_list_pro = sort_drivers_by_points(drivers_list_pro)
    drivers_list_pro = []
    teams_list_pro = []
    for driver in sorted_list_pro:
        drivers_list_pro.append(driver.to_json())
        team_pro = next((tm for tm in teams_list_pro if tm.name == driver.team), None)
        if team_pro is None:
            team = next((tm for tm in teams_list if tm.name == driver.team), None)
            if team is not None:
                team.points += driver.points
                teams_list_pro.append(deepcopy(team))
        else:
            team_pro.points += driver.points
            teams_list_pro.sort(key=lambda x: x.points, reverse=True)

    sorted_list_silver = sort_drivers_by_points(drivers_list_silver)
    drivers_list_silver = []
    teams_list_silver = []
    for driver in sorted_list_silver:
        drivers_list_silver.append(driver.to_json())
        team_silver = next((tm for tm in teams_list_silver if tm.name == driver.team), None)
        if team_silver is None:
            team = next((tm for tm in teams_list if tm.name == driver.team), None)
            if team is not None:
                team.points += driver.points
                teams_list_pro.append(deepcopy(team))
        else:
            team_pro.points += driver.points
            teams_list_pro.sort(key=lambda x: x.points, reverse=True)

    team_list_am = []
    for team in teams_list_am:
        team_list_am.append(team.to_json())
    
    team_list_pro = []
    for team in teams_list_pro:
        team_list_pro.append(team.to_json())

    team_list_silver = []
    for team in teams_list_silver:
        team_list_silver.append(team.to_json())

    return drivers_list_pro, drivers_list_am, drivers_list_silver, team_list_pro, team_list_am, team_list_silver
