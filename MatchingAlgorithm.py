from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np
import json

def create_data_model(time_matrix, time_window, revenues, num_vehicles, servicing_times):
    """
    Purpose of this function is to store the data for the problem.

    time_matrix: A 2-d Array of Travel times between locations. Format is specified in Feature Engineering.py file

    time_window: An array of time window tuples for each locations, requested times for the visit that MUST be fulfilled.
                Format = [(X, X+60) ... (N, N+60)]
                Note that at Index 0, it is the ending/pickup location, time window is set to the Break Time
                and for Index 1 to  M (where M is the number of Phlebotomists), those are phlebotomists' starting locations
                therefore time windows are set based on their starting time
    
    revenues: A 1-d Array of revenues of each orders/order locations
            Format = [1 ... N]
            Note that at Index 0, it is the ending/pickup location, revenue is set arbitrarily at $1 
            and for Index 1 to  M (where M is the number of Phlebotomists), those are phlebotomists' starting locations
            revenue is also set arbitrarily at $1. However, those values are trivial and will not affect the algorithm
    
    num_vehicles: A single digit for the number of Phlebotomists available for allocation

    servicing_times: An 1-d array for each order's servicing time required. Note that from Index 0 to M phlebotomists of the array
            trivial, so can just set any arbritrary number (e.g. 0).
    """

    data = {}

    time_matrix = np.array(time_matrix)
    # Take into account of servicing times
    for col_idx in range(len(servicing_times)):
        time_matrix[:, col_idx] += servicing_times[col_idx]
    
    data['time_matrix'] = time_matrix

    data['time_windows'] = time_window
    data['revenue_potential'] = revenues
    data['num_vehicles'] = num_vehicles

    data['starts'] = [i for i in range(1, num_vehicles+1)] #start locations
    data['ends'] = [0 for _ in range(num_vehicles)] #end location
    data['demands'] = [1 if _ > num_vehicles else 0 for _ in range(1, len(time_matrix) + 1)] 
    data['vehicle_capacities'] = [20 for _ in range(num_vehicles)]
    data['servicing_times'] = servicing_times
    return data

class npEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.int32):
            return int(obj)
        return json.JSONEncoder.default(self, obj)
    
def output_jsonify(data, manager, routing, solution):
    
    output = {}
    model = {}
    routes = []

    model['Objective Number'] = solution.ObjectiveValue()
    model['Status'] = routing.status()

    # Dropped Nodes/Customers
    total_revenue_lost = 0
    total_node_drops = 0
    dropped_nodes = []
    dropped_revenues = []
    for node in range(routing.Size()):
        if routing.IsStart(node) or routing.IsEnd(node):
            continue
        if solution.Value(routing.NextVar(node)) == node:
            dropped_nodes.append(manager.IndexToNode(node))
            dropped_revenues.append(data['revenue_potential'][manager.IndexToNode(node)])
            total_revenue_lost += data['revenue_potential'][manager.IndexToNode(node)]
            total_node_drops += 1
    
    model['Total Revenue Lost'] = total_revenue_lost
    model["Total Number of Nodes Dropped"] = total_node_drops
    model["Nodes Dropped"] = dropped_nodes
    model["Revenues Dropped"] = dropped_revenues
    

    # Routes
    time_dimension = routing.GetDimensionOrDie('Time')
    total_time = 0
    total_load = 0
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        prev_index = 0

        phleb_route = {}
        route_locations = []
        route_startTimes =[]
        route_endTimes = []
        route_slackTimes = []
        phleb_route['Phlebotomist Index'] = vehicle_id

        plan_output = 'Route for Phlebotomist {}:\n'.format(vehicle_id)

        route_load = 0
        total_transit_time = 0 
        while not routing.IsEnd(index):
            time_var = time_dimension.CumulVar(index)
            slack_var = time_dimension.SlackVar(index)

            node_index = manager.IndexToNode(index)
            route_load += data['demands'][node_index]

            plan_output += 'Location {0} Start({1},{2}) End({3}, {4}) -> Slack({5}, {6}) -> '.format(
                manager.IndexToNode(index), 
                solution.Min(time_var) - data['servicing_times'][node_index], solution.Max(time_var) - data['servicing_times'][node_index],
                solution.Min(time_var) , solution.Max(time_var),
                solution.Min(slack_var), solution.Max(slack_var))
            
            route_locations.append(manager.IndexToNode(index))
            route_startTimes.append((solution.Min(time_var) - data['servicing_times'][node_index], solution.Max(time_var) - data['servicing_times'][node_index]))
            route_endTimes.append((solution.Min(time_var) , solution.Max(time_var)))
            route_slackTimes.append((solution.Min(slack_var), solution.Max(slack_var)))
            
            prev_index = index
            index = solution.Value(routing.NextVar(index))
      
            total_transit_time = total_transit_time + data['time_matrix'][manager.IndexToNode(prev_index)][manager.IndexToNode(index)] - data['servicing_times'][manager.IndexToNode(index)]

        total_time += total_transit_time
        time_var = time_dimension.CumulVar(index)

        plan_output += 'Location {0} Time({1},{2})\n'.format(manager.IndexToNode(index),
                                                    solution.Min(time_var),
                                                    solution.Max(time_var))
        
        route_locations.append(manager.IndexToNode(index))
        route_startTimes.append((solution.Min(time_var),  solution.Max(time_var)))
        route_endTimes.append((solution.Min(time_var) , solution.Max(time_var)))

        phleb_route['Printable Route'] = plan_output
        phleb_route['Total Travel Time'] = total_transit_time
        phleb_route['Total Loads'] = route_load
        phleb_route['Locations Sequence'] = route_locations
        phleb_route['Start Times Sequence'] = route_startTimes
        phleb_route['End Times Sequence'] = route_endTimes
        phleb_route['Slack Times Sequence'] = route_slackTimes

        routes.append(phleb_route)

        total_load += route_load
    
    model['Total Travel Time'] = total_time
    model['Total Loads'] = total_load

    output['Model'] = model
    output['Routes'] = routes

    return json.dumps(output, indent=2, cls=npEncoder)


def run_algorithm(time_matrix, order_window, revenues, numPhleb, servicing_times):
    # Instantiate the data problem.
    data = create_data_model(time_matrix, order_window, revenues, numPhleb, servicing_times)

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(len(data['time_matrix']),
                                           data['num_vehicles'],
                                           data['starts'],
                                           data['ends']
                                           )

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)


    # Create and register a transit callback.
    def time_callback(from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to time matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['time_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(time_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    '''Add demand_callback '''
    def demand_callback(from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(
        demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        data['vehicle_capacities'],  # vehicle maximum capacities
        True,  # start cumul to zero
        'Capacity')

    # Allow to drop nodes.
    for node in range(1, len(data['time_matrix'])):
        penalty = data['revenue_potential'][manager.NodeToIndex(node)]
        routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

    # Add Time Windows constraint.
    time = 'Time'
    routing.AddDimension(
        transit_callback_index,
        1000,  # maximum Slack time 
        1000,  # maximum time per vehicle 
        False,  # Don't force start cumul to zero.
        time)
    time_dimension = routing.GetDimensionOrDie(time)

    # Add time window constraints for each location except depot
    for location_idx, time_window in enumerate(data['time_windows']):
        if location_idx == 0:
            continue
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0] + data['servicing_times'][index], time_window[1] + data['servicing_times'][index])
        routing.AddToAssignment(time_dimension.SlackVar(index))

    # Add time window constraints for each vehicle start node.
    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(
            int(data["time_windows"][0][0]), int(data["time_windows"][0][1]))
        routing.AddToAssignment(time_dimension.SlackVar(index))

    for i in range(data["num_vehicles"]):
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.Start(i))
        )
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.End(i))
        )

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.seconds = 30

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    # Print solution on console.
    if solution:
        return output_jsonify(data, manager, routing, solution)
    else:
        return 'Routing Status: ' + routing.status

