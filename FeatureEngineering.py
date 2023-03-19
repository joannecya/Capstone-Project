import json
import urllib
import urllib.request
import numpy as np

def create_time_matrix(address_list, api):
    addresses = address_list
    API_key = api
    # Distance Matrix API only accepts 100 elements per request, so get rows in multiple requests.
    # Maximum number of rows that can be computed per request (9 * 9 = 81).
    max_rows = 9
    num_addresses = len(addresses)  
    # num_addresses = q * max_rows + r 
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
        if len(addresses) > 1:
            for i in range(len(addresses) - 1):
                address_str += addresses[i] + '|'
            
            address_str += addresses[-1]
        else:
            address_str = addresses[0]
        return address_str

    request = 'https://maps.googleapis.com/maps/api/distancematrix/json?units=metric'
    origin_address_str = build_address_str(origin_addresses)
    dest_address_str = build_address_str(dest_addresses)
    request = request + '&origins=' + origin_address_str + '&destinations=' + \
        dest_address_str + '&key=' + API_key
    
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


'''
Other Preprocessing Codes
'''

def get_coordinates_list(orders_df, catchments_df, phlebs_df):
    orders_df = orders_df.astype({'long': str, 'lat': str})
    catchments_df = catchments_df.astype({'long': str, 'lat': str})
    phlebs_df = phlebs_df.astype({'home_long': str, 'home_lat': str})
    
    orders_df['Address'] = orders_df['lat'].str.cat(orders_df['long'], sep=',')
    catchments_df['Address'] = catchments_df['lat'].str.cat(catchments_df['long'], sep=',')
    phlebs_df['Address'] = phlebs_df['home_lat'].str.cat(phlebs_df['home_long'], sep=',')

    addresses_list = []
    if catchments_df.shape[0] == 1:
        addresses_list.append(catchments_df['Address'].iloc[0])
        #Phlebotomists' Starting Points second
        addresses_list.extend(phlebs_df['Address'])
        #Orders' Locations last
        addresses_list.extend(orders_df['Address'])
    else:
        addresses_list.extend(catchments_df['Address'])
        addresses_list.extend(phlebs_df['Address'])
        addresses_list.extend(orders_df['Address'])
        
    return addresses_list

def get_timeWindows_list(orders_df, catchments_df, phlebs_df):
    time_window = [(6 * 60, 18 * 60)] #ending depot
    time_window.extend([(int(start) * 60, (int(start)+1) * 60) for start in phlebs_df['shift_start']])
    time_window.extend([(int(start) * 60, int(start+1) * 60) for start in orders_df['order_start']])
    return time_window

def get_servicingTimes_list(orders_df, catchments_df, phlebs_df):
    numPhleb = phlebs_df.shape[0]
    servicing_times = [0]
    servicing_times.extend([0 for _ in range(numPhleb)])
    servicing_times.extend(orders_df['duration'] + orders_df['buffer'])
    return servicing_times

def get_inverseRatings_list(orders_df, catchments_df, phlebs_df):
    inverse_ratings = 5 - phlebs_df['service_rating']
    return inverse_ratings

def get_orderRevenues_list(orders_df, catchments_df, phlebs_df):
    numPhleb = phlebs_df.shape[0]
    revenues = [1] #ending depot
    revenues.extend([1 for _ in range(numPhleb)])
    revenues.extend(orders_df['price'])
    return revenues

def get_serviceExpertiseConstraint_list(orders_df, catchments_df, phlebs_df):
    def find_applicable_exp(row):
        args = np.empty(0)
        for val in row:
            args = np.append(args, val)
        idx = [args == 1]
        service_needs = service_cols[idx[0]]

        expertiseName = "expertise_{}".format(service_needs[0].split("_")[1])
        temp = phlebs_df.loc[(phlebs_df[expertiseName] == 1)]

        if len(service_needs) > 1:
            for service in service_needs[1:]:
                expertiseName = "expertise_{}".format(service.split("_")[1])
                temp = temp.loc[(temp[expertiseName] == 1)]  
        return temp.index.to_list()
    
    numPhleb = phlebs_df.shape[0]
    all_columns = orders_df.columns
    service_cols = all_columns[all_columns.str.contains('service')]
    orders_df['Acceptable Phleb Indices'] = orders_df[service_cols].apply(find_applicable_exp, axis=1)
    expertises = [1] #ending depot
    expertises.extend([1 for _ in range(numPhleb)])
    expertises.extend(orders_df['Acceptable Phleb Indices'])
    return expertises

def get_metadata(orders_df, catchments_df, phlebs_df):
    numPhleb = phlebs_df.shape[0]
    numCatchment = catchments_df.shape[0]

    #If there is only 1 catchment area, we will put it in the Front
    if catchments_df.shape[0] == 1:
        order_ids = ["Ending Location"] #ending catchment
        order_ids.extend(["Starting Location" for _ in range(numPhleb)])
        order_ids.extend(orders_df['order_id'])
        addresses_list = get_coordinates_list(orders_df, catchments_df, phlebs_df)
        locations_metadata = zip(addresses_list, order_ids)
        metadata = {'Locations': [{"Location Index": idx, "Coordinate": metadata[0], "Order Id": str(metadata[1])}for idx, metadata in enumerate(locations_metadata)]}
        metadata['Phlebotomists'] = [{"Phlebotomist Index": idx, "Id": id}for idx, id in enumerate(phlebs_df['phleb_id'])]
    else:
    #If there more than 1 catchment area, index 0 will just be a trivial placeholder, so not to disrupt other inputs' format, 
    # and we will add ending catchments to the End instead
        order_ids = ["Placeholder"]
        order_ids.extend(["Starting Location" for _ in range(numPhleb)])
        order_ids.extend(orders_df['order_id'])
        order_ids.extend(["Ending Location" for _ in range(numCatchment)]) #catchment areas
        addresses_list = ["Placeholder"]
        addresses_list.extend(get_coordinates_list(orders_df, catchments_df, phlebs_df))
        locations_metadata = zip(addresses_list, order_ids)
        metadata = {'Locations': [{"Location Index": idx, "Coordinate": metadata[0], "Order Id": str(metadata[1])}for idx, metadata in enumerate(locations_metadata)]}
        metadata['Phlebotomists'] = [{"Phlebotomist Index": idx, "Id": id}for idx, id in enumerate(phlebs_df['phleb_id'])]
    
    return metadata