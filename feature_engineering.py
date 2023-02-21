import requests
import json
import urllib
import urllib.request


def create_data(addresses):
  """Creates the data."""
  data = {}
  data['API_key'] = ''
  data['addresses'] = addresses
  return data

def create_time_matrix(data):
    addresses = data["addresses"]
    API_key = data["API_key"]
    # Distance Matrix API only accepts 100 elements per request, so get rows in multiple requests.
    max_elements = 100
    num_addresses = len(addresses)  # 26 in this example.
    # Maximum number of rows that can be computed per request (3 in this example).
    max_rows = max_elements // num_addresses
    # num_addresses = q * max_rows + r (q = 8 and r = 2 in this example).
    q, r = divmod(num_addresses, max_rows)
    dest_addresses = addresses
    time_matrix = []
    for i in range(q):
        row_time_matrix = []
        origin_addresses = addresses[i * max_rows: (i + 1) * max_rows]
        for j in range(q):
            dest_addresses = addresses[j * max_rows: (j + 1) * max_rows]
            response = send_request(origin_addresses, dest_addresses, API_key)
            if len(row_time_matrix) == 0:
                row_time_matrix += build_time_matrix(response)
            else:
                for numRow  in range(len(row_time_matrix)):
                    row_time_matrix[numRow] += build_time_matrix(response)[numRow]
        if r > 0:
            dest_addresses_r = addresses[(q * max_rows): (q * max_rows) + r]
            response = send_request(origin_addresses, dest_addresses_r, API_key)
            for numRow  in range(len(row_time_matrix)):
                    row_time_matrix[numRow] += build_time_matrix(response)[numRow]

        time_matrix += row_time_matrix

    # Get the remaining remaining r rows, if necessary.
    if r > 0:
        row_time_matrix = []
        origin_addresses = addresses[q * max_rows: q * max_rows + r]
        for j in range(q):
            dest_addresses = dest_addresses = addresses[j * max_rows: (j + 1) * max_rows]
            response = send_request(origin_addresses, dest_addresses, API_key)
            if len(row_time_matrix) == 0:
                row_time_matrix += build_time_matrix(response)
            else:
                for numRow  in range(len(row_time_matrix)):
                    row_time_matrix[numRow] += build_time_matrix(response)[numRow]
        
        dest_addresses_r = addresses[(q * max_rows): (q * max_rows) + r]
        response = send_request(origin_addresses, dest_addresses_r, API_key)
        for numRow  in range(len(row_time_matrix)):
                    row_time_matrix[numRow] += build_time_matrix(response)[numRow]

        time_matrix += row_time_matrix
        
    return time_matrix


def send_request(origin_addresses, dest_addresses, API_key):
    """ Build and send request for the given origin and destination addresses."""
    def build_address_str(addresses):
        # Build a pipe-separated string of addresses
        address_str = ''
        for i in range(len(addresses) - 1):
            address_str += addresses[i] + '|'
        address_str += addresses[-1]
        return address_str

    request = 'https://maps.googleapis.com/maps/api/distancematrix/json?units=metric'
    origin_address_str = build_address_str(origin_addresses)
    dest_address_str = build_address_str(dest_addresses)
    request = request + '&origins=' + origin_address_str + '&destinations=' + \
        dest_address_str + '&key=' + API_key
    #jsonResult = urllib.urlopen(request).read()
    with urllib.request.urlopen(request) as url:
        jsonResult = url.read()
        response = json.loads(jsonResult)
        return response

def secondsToMinutes(seconds):
    return int(seconds/60)

def build_time_matrix(response):
    time_matrix = []
    for row in response['rows']:
        row_list = [secondsToMinutes(row['elements'][j]['duration']['value'])
                    for j in range(len(row['elements']))]
        time_matrix.append(row_list)
    return time_matrix

########
# Main #
########
def main(addresses):
  """Entry point of the program"""
  # Create the data.
  data = create_data(addresses)
  API_key = data['API_key']
  time_matrix = create_time_matrix(data)
  return time_matrix

if __name__ == '__main__':
  main()