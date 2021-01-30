#!/usr/bin/env python3

''' Script to fetch historical Octopus Agile pricing for a whole year '''

import calendar
from datetime import datetime
import requests

# Year to fetch
YEAR = 2020

# URL parts - see https://developer.octopus.energy/docs/api/#agile-octopus

BASE_URL = 'https://api.octopus.energy'
PRODUCT_CODE = 'AGILE-18-02-21'
MPAN_REGION = 'A'
TARIFF_CODE = 'E-1R-' + PRODUCT_CODE + '-' + MPAN_REGION
TARIFF_URL = BASE_URL + '/v1/products/' + PRODUCT_CODE + '/electricity-tariffs/' + TARIFF_CODE + '/standard-unit-rates'

def get_months_data(year, month):
    ''' Get the agile price data for the given year and month.

        Returns a dictionary with entries for each day,
        indexed by integer day number and each entry an array
        of half hourly float prices for the day.

        On failure returns empty dictionary.
    '''
    prices = {}

    try:
        # Start and end range - collect the whole month
        start = "{0}-{1:02}-01T00:00Z".format(year, month)
        if month < 12:
            end = "{0}-{1:02}-01T00:00Z".format(year, month+1)
        else:
            end = "{0}-{1:02}-01T00:00Z".format(year+1, 1)

        req = requests.get(TARIFF_URL, params={'period_from': start, 'period_to': end, 'page_size': 1500})
        req.raise_for_status()

        result_prices = req.json()['results']

        # Extract the price data, indexed by time
        price_data = {}
        for result in result_prices:
            time = datetime.strptime(result['valid_from'], '%Y-%m-%dT%H:%M:%S%z')
            price = result['value_inc_vat']
            if (time is not None) and (price is not None):
                # Store with integer timestamp as key for easy sorted access later
                price_data[int(time.timestamp())] = price
            else:
                print('malformed result: {0}'.format(result))

        # Finally, prices is a dict with array for each day of half hourly prices

        # Check we got the expected number of half hour prices
        (_, days_in_month) = calendar.monthrange(YEAR, month)
        if len(price_data) == (48 * days_in_month):
            # Now build an array of prices for each day
            count = 0
            for time, price in sorted(price_data.items()):
                day = int((count / 48) + 1)
                if count % 48 == 0:
                    prices[day] = []
                prices[day].append(str(price))
                count = count + 1
        else:
            print('Failed to get results for month {0}. Got {1} prices'.format(month, len(prices)))

    except (requests.HTTPError, ValueError) as err:
        print(err)

    return prices

def fetch_data(year):
    ''' Fetch the agile prices for the given year '''
    year_data = []
    for month in range(1, 13):
        prices = get_months_data(year, month)
        if len(prices) > 0:
            for _, day_prices in prices.items():
                year_data.append(day_prices)
        else:
            print("failed to get the years data")
            return
    # Write data to file
    with open('agile_{0}.txt'.format(year), 'w') as file_handle:
        for hh_array in year_data:
            day_costs = ','.join(hh_array)
            file_handle.write(day_costs+'\n')

fetch_data(YEAR)
