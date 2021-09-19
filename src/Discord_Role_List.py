import sys
from pymongo import MongoClient
from ACC_Credentials import MONGO_LINK

MONGO_CLIENT = MongoClient(MONGO_LINK)
ACC_COLLECTION = MONGO_CLIENT.isda

def get_discord_names(season_id):
    season = ACC_COLLECTION.Seasons.find_one({'id': season_id})
    if season is None:
        sys.exit(1)
    discord_ids = []
    not_found_discord_ids = []
    for entry in season['entries']:
        car = ACC_COLLECTION.Cars.find_one({'id': entry})
        for steam_id in car['drivers']:
            driver = ACC_COLLECTION.Drivers.find_one({'steam_guid': steam_id})
            if 'discord_id' in driver and driver['discord_id'] is not None:
                discord_ids.append(driver['discord_id'])
            else:
                not_found_discord_ids.append(driver['real_name'])
    return discord_ids, not_found_discord_ids

if __name__ == '__main__':
    print('ISDA - Discord List Generator')
    season_id = input('Enter season ID: ')
    discord_ids, real_names = get_discord_names(season_id)
    with open('Drivers_Discord.txt', 'w', encoding="utf-8") as openfile:
        openfile.write('Found Discord IDs:\n')
        for discord_id in discord_ids:
            openfile.write(discord_id + '\n')
        openfile.write('\nDiscord IDs not found for:\n')
        for real_name in real_names:
            openfile.write(real_name + '\n')
    print('All names flushed to Drivers_Discord.txt')