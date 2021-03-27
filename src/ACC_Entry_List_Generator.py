import json
import sys
from ACC_Credentials import MONGO_LINK
from pymongo import MongoClient

MONGO_CLIENT = MongoClient(MONGO_LINK)
ACC_COLLECTION = MONGO_CLIENT.isda

class Driver():
    def __init__(self, steam_id, name='', surname='', shortname='', category=3):
        self.steam_id = steam_id
        self.name = name
        self.surname = surname
        self.shortname = shortname
        self.category = category

    def populate_driver_data(self):
        driver_data = ACC_COLLECTION.Drivers.find_one({'steam_guid': self.steam_id})
        if driver_data is not None:
            splitted_string = driver_data['display_name'][0].split(' ')
            abbreviation_index = 1
            for i in range(1, len(splitted_string)):
                if splitted_string[i].isupper() and len(splitted_string[i]) == 3:
                    abbreviation_index = i
                    break
            name = ''
            surname = ''
            for i in range(len(splitted_string)):
                if i < abbreviation_index:
                    name += ' '
                    name += splitted_string[i]
                elif i > abbreviation_index:
                    surname += ' '
                    surname += splitted_string[i]
            self.name = name[1:]
            self.shortname = splitted_string[abbreviation_index]
            self.surname = surname[1:]

    def to_dict(self):
        return {
            'firstName': self.name,
            'lastName': self.surname,
            'shortName': self.shortname,
            'playerID': self.steam_id,
            'driverCategory': self.category
        }

class Entry():
    def __init__(self, drivers=[], car_id = '', number=0, car=0, admin=0):
        self.drivers = drivers
        self.number = number
        self.car = car
        self.car_id = car_id
        self.admin = admin

    def populate_data(self):
        car_info = ACC_COLLECTION.Car_Types.find_one({'id': self.car_id})
        if car_info is not None:
            self.car = car_info['game_ids']['acc']
        
        for driver in self.drivers:
            driver.populate_driver_data()


    def to_dict(self):
        driver_dict = []
        for driver in self.drivers:
            driver_dict.append(driver.to_dict())
        return {
            'drivers': driver_dict,
            'raceNumber': int(self.number),
            'forcedCarModel': int(self.car),
            'overrideDriverInfo': 1,
            'isServerAdmin': 0
        }

if (len(sys.argv) != 2):
    sys.exit(1)
season = ACC_COLLECTION.Seasons.find_one({'id': sys.argv[1]})
if season is None:
    sys.exit(1)
registered_entries = ACC_COLLECTION.Cars.find({'id': {'$in': season['entries']}})
entry_list = []
for entry in registered_entries:
    driver_list = []
    for steamid in entry['drivers']:
        driver_list.append(Driver(steamid))
    car = Entry(drivers=driver_list, car_id=entry['car_type'], number=entry['entry_number'])
    car.populate_data()
    entry_list.append(car.to_dict())

entry_list_dict = {
    'entries': entry_list,
    'forceEntryList': 1
}

with open('entrylist.json', 'w', encoding="utf-16-le") as outfile:
    json.dump(entry_list_dict, outfile, indent=2, ensure_ascii=False)