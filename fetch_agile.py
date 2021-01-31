#!/usr/bin/env python3

''' Script to fetch historical Octopus Agile pricing for a whole year '''

import calendar
from datetime import datetime
import argparse
import requests

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
        (_, days_in_month) = calendar.monthrange(year, month)
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

def fetch_data(year, start_month, num_months, output_file):
    ''' Fetch the agile prices for the given year '''
    year_data = []
    for month in range(start_month, (start_month + num_months)):
        prices = get_months_data(year, month)
        if len(prices) > 0:
            for _, day_prices in prices.items():
                year_data.append(day_prices)
        else:
            print("failed to get the years data")
            return
    # Write data to file
    with open(output_file, 'w') as file_handle:
        for hh_array in year_data:
            day_costs = ','.join(hh_array)
            file_handle.write(day_costs+'\n')

# -------------------------------------------------------------------------
# Main entry point
# -------------------------------------------------------------------------

# Create an options parser
PARSER = argparse.ArgumentParser(description="Fetch Octopus agile historical price data",
                                 fromfile_prefix_chars='@')

PARSER.add_argument('output_file', nargs=1, type=str,
                    help='the output file name')

PARSER.add_argument('-y', '--year', metavar='<year>',
                    dest="year", type=int, default=2020,
                    help="the year from which to fetch data")

PARSER.add_argument('-m', '--month', metavar='<month>',
                    dest="month", type=int, default=1,
                    help="the starting month from which to fetch")

PARSER.add_argument('-n', '--num-months', metavar='<num-months>',
                    dest="num_months", type=int, default=12,
                    help="the number of months data to fetch")

# Run the parser, exiting on error
ARGS = PARSER.parse_args()

fetch_data(ARGS.year, ARGS.month, ARGS.num_months, ARGS.output_file[0])
