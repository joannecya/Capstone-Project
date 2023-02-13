from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

def create_data_model():
    """Stores the data for the problem."""
    data = {}

    # Travel times between locations; calculated as (1)Time to Travel + (2) Servicing Time + (3) Buffer Time; 
    # each will manipulable variable during Pipeline design for Feature Engineering
    data['time_matrix'] = [
        [0, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        [0.1, 0,  0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.2],
        [0.2, 0.1, 0, 0.1, 0.1, 0.2, 0.3, 0.2, 0.1],
        [0.2, 0.1, 0.2, 0, 0.1, 0.2, 0.3, 0.2, 0.1],
        [0.2, 0.1, 0.2, 0.1, 0, 0.2, 0.3, 0.2, 0.1],
        [0.3, 0.2, 0.1, 0.2, 0.1, 0, 0.2, 0.3, 0.2],
        [0.2, 0.1, 0.2, 0.1, 0.1, 0.2, 0, 0.3, 0.2],
        [0.2, 0.4, 0.2, 0.1, 0.2, 0.1, 0.1, 0, 0.2],
        [0.3, 0.2, 0.1, 0.2, 0.1, 0.2, 0.1, 0.1, 0],
    ]

    # An array of time windows for the locations, requested times for the visit that MUST be fulfilled.
    data['time_windows'] = [
        (0, 14),  # 0
        (0, 1),  # 1
        (1, 2),  # 2
        (7, 8),  # 3
        (8, 9),  # 4
        (4, 5),  # 5
        (2, 3),  # 6
        (6, 7),  # 7
        (3, 4),  # 8
    ]
    data['num_vehicles'] = 2
    data['starts'] = [1, 2]
    data['ends'] = [0, 0]
    data['demands'] = [0, 0, 0, 1, 1, 1, 1, 1, 1]
    data['vehicle_capacities'] = [3, 4]
    return data


def print_solution(data, manager, routing, solution):
    
    """Prints solution on console."""
    print(f'Objective: {solution.ObjectiveValue()}')
    time_dimension = routing.GetDimensionOrDie('Time')
    total_time = 0
    total_load = 0
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        plan_output = 'Route for Phlebotomist {}:\n'.format(vehicle_id)
        route_load = 0
        while not routing.IsEnd(index):
            time_var = time_dimension.CumulVar(index)

            node_index = manager.IndexToNode(index)
            route_load += data['demands'][node_index]

            plan_output += '{0} Time({1},{2}) -> '.format(
                manager.IndexToNode(index), solution.Min(time_var),
                solution.Max(time_var))
            index = solution.Value(routing.NextVar(index))
        time_var = time_dimension.CumulVar(index)
        plan_output += 'Location {0} Time({1},{2})\n'.format(manager.IndexToNode(index),
                                                    solution.Min(time_var),
                                                    solution.Max(time_var))
        plan_output += 'Time of the route: {}min\n'.format(
            solution.Min(time_var))
        print(plan_output)
        total_time += solution.Min(time_var)
        total_load += route_load
    print('Total time of all routes: {}min'.format(total_time))
    print('Total load of all routes: {}'.format(total_load))


def main():
    """Solve the VRP with time windows."""
    # Instantiate the data problem.
    data = create_data_model()

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

    # Add Time Windows constraint.
    time = 'Time'
    routing.AddDimension(
        transit_callback_index,
        30,  # allow waiting time
        30,  # maximum time per vehicle
        False,  # Don't force start cumul to zero.
        time)
    time_dimension = routing.GetDimensionOrDie(time)

    # Add time window constraints for each location except start positions (houses of Phebotomists).
    for location_idx, time_window in enumerate(data['time_windows']):
        if location_idx == 0 or location_idx == 1:
            continue
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

    # Add time window constraints for each vehicle start node.
    index = routing.Start(0)
    time_dimension.CumulVar(index).SetRange(data['time_windows'][0][0],data['time_windows'][0][1])

    # Instantiate route start and end times to produce feasible times.
    for i in range(data['num_vehicles']):
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.Start(i)))
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.End(i)))

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
        print_solution(data, manager, routing, solution)


main()