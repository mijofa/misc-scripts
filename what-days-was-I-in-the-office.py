#!/usr/bin/python3
"""Read Google's Takeout data for location history to determine what days I was in the office."""
import json
# import pprint
import datetime

work_address = '49/45 Riversdale Rd, Hawthorn VIC 3122, Australia'
work_dates = set()

for filename in ['2021/2021_JULY.json', '2021/2021_AUGUST.json', '2021/2021_SEPTEMBER.json',
                 '2021/2021_OCTOBER.json', '2021/2021_NOVEMBER.json', '2021/2021_DECEMBER.json',
                 '2022/2022_JANUARY.json', '2022/2022_FEBRUARY.json', '2022/2022_MARCH.json',
                 '2022/2022_APRIL.json', '2022/2022_MAY.json', '2022/2022_JUNE.json']:
    month = json.load(open(filename, 'r'))
    locations_visited = [{'probable': place['placeVisit']['location']['address'],
                          'candidates': [candidate['address'] for candidate in place['placeVisit']['otherCandidateLocations']
                                         if 'address' in candidate],
                          'startDate': datetime.datetime.strptime(
                              place['placeVisit']['duration']['startTimestamp'].partition('.')[0].strip('Z'),
                              '%Y-%m-%dT%H:%M:%S').date(),
                          'endDate': datetime.datetime.strptime(
                              place['placeVisit']['duration']['endTimestamp'].partition('.')[0].strip('Z'),
                              '%Y-%m-%dT%H:%M:%S').date(),
                          } for place in month['timelineObjects'] if 'placeVisit' in place]
    for location in locations_visited:
        if location['probable'].endswith(work_address) or any([a.endswith(work_address) for a in location['candidates']]):
            work_dates.add(location['startDate'])
            work_dates.add(location['endDate'])

for d in sorted(work_dates):
    print(d)
