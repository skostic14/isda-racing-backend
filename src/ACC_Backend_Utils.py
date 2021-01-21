import datetime

# Gets time from milliseconds
# Returns string formatted as HH:MM:SS:mmm, MM:SS:mmm or S:mmm, depending on the time. 
def get_time_from_milliseconds(milli):
    milliseconds = milli % 1000
    seconds= (milli//1000)%60
    minutes= (milli//(1000*60))%60
    hours= (milli//(1000*60*60))%24

    if hours == 0: 
        if minutes == 0:
            return '%d.%03d' % (seconds, milliseconds)
        return '%02d:%02d.%03d' % (minutes, seconds, milliseconds)
    return '%02d:%02d:%02d.%03d' % (hours, minutes, seconds, milliseconds)

# Returns a string formatted as YYYY-MM-DD
def get_date_today():
    return datetime.date.today().strftime("%Y-%m-%d")