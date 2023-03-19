import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import geopandas as gpd
from shapely.geometry import Point, LineString
import plotly_express as px
import networkx as nx
import osmnx as ox
import folium

def to_time(time_window):
    """
    Converts a time window into a presentable string format

    Arguments:
        time_window: list containing 2 elements - start and end of time window in minutes passed since 12am
    """
    start = divmod(time_window[0], 60) # returns (hour, minutes)
    end = divmod(time_window[1], 60)
    
    return(f"{start[0]:02d}:{start[1]:02d}  - {end[0]:02d}:{end[1]:02d}")

def create_popup(text):
    iframe = folium.IFrame(text)
    popup = folium.Popup(iframe,
                        min_width=300,
                        max_width=300)
    return popup


def visualise_routes(json_result, polygon, addresses_list):
    """
    Visualise realistic routes for each phlebotomist and saves them to a .html file

    Arguments:
        json_result: json output from Run Algorithm.ipynb (matching.json)
        polygon: geojson polygon provided by TATA
        addressess_list: list of addressess compiled - refer to Run Algorithm.ipynb 
    """
    # create base graph
    x_min, y_min, x_max, y_max = polygon.total_bounds
    G = ox.graph_from_bbox(north=y_max, south=y_min, east=x_max, west=x_min, network_type='drive')

    # colour and opacity of routes and markers
    colours = [
        'blue',
        'gray',
        'orange',
        'beige',
        'darkblue',
        'lightblue',
        'purple',
        'darkpurple',
        'pink',
        'cadetblue',
        'lightgray',
        'black'
    ]
    alpha = 0.5

    # catchment area 
    catchment_popup_text = "Catchment Area"
    catchment_coords = addresses_list[0].split(',')
    catchment_lat, catchment_long = float(catchment_coords[0]), float(catchment_coords[1])

    for j in range(len(json_result['Routes'])):
        phleb = json_result['Routes'][j]
        phleb_id = phleb['Phlebotomist Index']
        print(f"Creating route travelled by Phlebotomist ID #{phleb_id}")

        locations_sequence = phleb['Locations Sequence']
        print(locations_sequence)
        last_order_index = len(locations_sequence) - 2

        start_times = phleb['Start Times Sequence']
        end_times = phleb['End Times Sequence']

        colour = colours[j]
        print(colour)

        for i in range(len(locations_sequence)-1):
            start = addresses_list[locations_sequence[i]].split(',')
            end = addresses_list[locations_sequence[i+1]].split(',')
            start_lat, start_long = float(start[0]), float(start[1])
            end_lat, end_long = float(end[0]), float(end[1])

            start_node = ox.distance.nearest_nodes(G, Y=start_lat, X=start_long)
            end_node = ox.distance.nearest_nodes(G, Y=end_lat, X=end_long)

            route = nx.shortest_path(G, start_node, end_node, weight='distance')

            arrival_time = f"Arrival:{to_time(start_times[i])}"
            departure_time = f"Departure:{to_time(end_times[i])}"

            location_number = locations_sequence[i]
            order_id = json_result['Metadata']['Locations'][location_number]['Order Id']

            if i == 0:
                # phlebotomist home
                print(f"Map created for Phlebotomist ID #{phleb_id}'s route")
                if j == 0:
                    route_map = ox.plot_route_folium(G, route, route_linewidth=6, node_size=0, color=colour, opacity=alpha)
                else: 
                    route_map = ox.plot_route_folium(G, route, route_linewidth=6, node_size=0, route_map=route_map, color=colour, opacity=alpha)
                # create markers
                start_marker = folium.Marker(
                    location=(start_lat, start_long), # only accepts coords in tuple form
                    popup=create_popup(f"Phlebotomist #{phleb_id} Home<br>{departure_time}"),
                    icon = folium.Icon(color='green', icon='house', prefix='fa')
                )
                start_marker.add_to(route_map)
            else:
                # if map has been created, add onto route map
                route_map = ox.plot_route_folium(G, route, route_linewidth=6, node_size=0, route_map=route_map, color=colour, opacity=alpha)
                start_marker = folium.Marker(
                    location=(start_lat, start_long), # only accepts coords in tuple form
                    popup=create_popup(f'Order #{order_id}<br>{arrival_time}<br>{departure_time}'),
                    icon = folium.Icon(color=colour, icon='user', prefix='fa')
                )
                start_marker.add_to(route_map)

                if i == last_order_index:
                    catchment_popup_text += f"<br>Phlebotomist #{phleb_id} Arrival:{to_time(start_times[i+1])}"
                    print(f"Last order for Phlebotomist ID #{phleb_id} fulfilled")
                    # save map at the end of last order
                    print(f"Route travelled by Phlebotomist ID #{phleb_id} saved")
            
    catchment_marker = folium.Marker(
                    location=(catchment_lat, catchment_long), # only accepts coords in tuple form
                    popup=create_popup(f'{catchment_popup_text}'),
                    icon = folium.Icon(color='red', icon='vial', prefix='fa')
                )
    catchment_marker.add_to(route_map)
    route_map.save(f"Route Visualisations/Route.html")
   
# for testing purposes
if __name__ == "__main__":
    with open("Route Visualisations/matching.json", "r") as read_file:
        json_result = json.load(read_file)
    json_result = json.loads(json_result)

    polygon = gpd.read_file("Simulation\Gurugram_sample_Polygon.geojson")

    addresses_list = ['28.484314452017287,77.08784537403447', '28.443423074966024,77.0864228696552', '28.44779634378927,77.04657462495449', '28.437283115842664,77.08363561384037', '28.426139873942272,77.09989980027176', '28.450975296139998,77.05707277162473', '28.4346276220027,77.10731046594978', '28.433803303996754,77.0815831101854', '28.440829814217103,77.05009232467279', '28.425023397747474,77.0933768886317', '28.437934021117723,77.08513002952219', '28.477749854110492,77.09063434989348', '28.48996623734903,77.0921778477132', '28.43207724256467,77.10740559477985', '28.44319553731333,77.07262034644641', '28.441460262857042,77.11217116399158', '28.418827407440464,77.08643447272122', '28.48019713242638,77.0907176889603', '28.451745009255756,77.06841123738455']
    
    visualise_routes(json_result, polygon, addresses_list)

def create_grid_df(size, ):
    grid = pd.DataFrame()
    grid['x'] = np.repeat(np.arange(0, size), size)
    grid['y'] = np.tile(np.arange(0, size), size)