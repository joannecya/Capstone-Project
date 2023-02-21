from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


def create_data_model(time_matrix, time_window, revenues, num_vehicles):
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
    """

    data = {}

    data['time_matrix'] = time_matrix
    data['time_windows'] = time_window
    data['revenue_potential'] = revenues
    data['num_vehicles'] = num_vehicles

    data['starts'] = [i for i in range(1, num_vehicles+1)] #start locations
    data['ends'] = [0 for _ in range(num_vehicles)] #end location
    data['demands'] = [1 if _ > num_vehicles else 0 for _ in range(1, len(time_matrix) + 1)] 
    data['vehicle_capacities'] = [20 for _ in range(num_vehicles)]
    return data

def print_solution(data, manager, routing, solution):
    
    """Prints solution on console."""
    print(f'Objective: {solution.ObjectiveValue()}')

    # Display dropped nodes.
    dropped_nodes = 'Dropped nodes:'
    for node in range(routing.Size()):
        if routing.IsStart(node) or routing.IsEnd(node):
            continue
        if solution.Value(routing.NextVar(node)) == node:
            dropped_nodes += ' {} (${})'.format(manager.IndexToNode(node), data['revenue_potential'][manager.IndexToNode(node)])
    print(dropped_nodes + '\n')

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

            plan_output += 'Location {0} Time({1},{2}) -> '.format(
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
    print('Total time of all routes: {}mins'.format(total_time))
    print('Total load of all routes: {}'.format(total_load))


def run_algorithm(time_matrix, order_window, revenues, numPhleb):
    # Instantiate the data problem.
    data = create_data_model(time_matrix, order_window, revenues, numPhleb)

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
        60,  # allow waiting time
        700,  # maximum time per vehicle
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
    else:
        print('No Solution')