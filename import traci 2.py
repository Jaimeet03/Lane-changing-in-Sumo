import traci

sumo_config = r"C:\Users\kaurk\Sumo\2025-08-10-20-53-31\osm.sumocfg"

rear_vehicle = "veh2"   # Fast car
front_vehicle = "veh5"  # Slow car in same lane
side_vehicle = "veh7"   # Car in adjacent lane blocking overtake
overtake_edge = "77355809#1"

# Parameters
overtake_distance_trigger = 1    # m to trigger overtaking
safe_return_distance = 2         # m to return to original lane
lane_position_fraction = 0.3     # start overtake after 30% of lane
lanechange_duration = 3          # sec

traci.start([
    "sumo-gui",
    "-c", sumo_config,
    "--start",
    "--delay", "200"
])

overtaking = False
original_lane_index = None
trigger_position = None
gap_created = False

while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep()

    if all(v in traci.vehicle.getIDList() for v in [rear_vehicle, front_vehicle, side_vehicle]):
        # Set constant speeds for front and side vehicles
        traci.vehicle.setMaxSpeed(front_vehicle, 15)  # slow lane
        traci.vehicle.setMaxSpeed(side_vehicle, 15)   # block lane
        traci.vehicle.setMaxSpeed(rear_vehicle, 25)   # faster car

        current_edge = traci.vehicle.getRoadID(rear_vehicle)

        # Get lane length only once
        if trigger_position is None and current_edge == overtake_edge:
            lane_id = traci.vehicle.getLaneID(rear_vehicle)
            lane_length = traci.lane.getLength(lane_id)
            trigger_position = lane_length * lane_position_fraction

        # Start overtaking
        if not overtaking and current_edge == overtake_edge:
            lane_pos = traci.vehicle.getLanePosition(rear_vehicle)
            if lane_pos >= trigger_position:
                leader_info = traci.vehicle.getLeader(rear_vehicle, overtake_distance_trigger)
                if leader_info and leader_info[0] == front_vehicle:
                    # Step 1: Slow side vehicle to create gap
                    traci.vehicle.setMaxSpeed(side_vehicle, 10)
                    gap_created = True

                    # Step 2: Change lane for rear_vehicle
                    original_lane_index = traci.vehicle.getLaneIndex(rear_vehicle)
                    num_lanes = traci.edge.getLaneNumber(current_edge)
                    target_lane_index = (original_lane_index + 1) % num_lanes
                    traci.vehicle.setLaneChangeMode(rear_vehicle, 0b000000000000)
                    traci.vehicle.changeLane(rear_vehicle, target_lane_index, lanechange_duration)
                    print(f"{rear_vehicle} overtaking {front_vehicle} by moving into lane {target_lane_index}")
                    overtaking = True

        # Return to lane after overtake
        elif overtaking and current_edge == overtake_edge:
            follower_info = traci.vehicle.getFollower(rear_vehicle, 100)
            if follower_info and follower_info[0] == front_vehicle and follower_info[1] > safe_return_distance:
                traci.vehicle.changeLane(rear_vehicle, original_lane_index, lanechange_duration)
                print(f"{rear_vehicle} returned to lane {original_lane_index} ahead of {front_vehicle}")
                overtaking = False

                # Step 3: Restore speed for side_vehicle
                if gap_created:
                    traci.vehicle.setMaxSpeed(side_vehicle, 15)
                    gap_created = False

traci.close()
