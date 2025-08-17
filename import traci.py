import traci

sumo_config = r"C:\Users\kaurk\Sumo\2025-08-10-20-53-31\osm.sumocfg"

rear_vehicle = "veh2"   # fast car
front_vehicle = "veh5"  # slow car
target_edge_for_overtake = "77355809#1"  # road where overtake happens

# Configurable parameters
overtake_distance_trigger = 1    # m, distance to start overtaking
safe_return_distance = 2         # m, gap needed to return to original lane
lane_position_fraction = 0.3     # 30% into the lane before starting overtake
lanechange_duration = 5          # sec

traci.start([
    "sumo-gui",
    "-c", sumo_config,
    "--start",
    "--quit-on-end",
    "--delay", "500"
])

overtaking = False
original_lane_index = None
trigger_position = None

while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep()

    # Slow car speed
    if front_vehicle in traci.vehicle.getIDList():
        traci.vehicle.setMaxSpeed(front_vehicle, 10)  # ~36 km/h

    # Fast car logic
    if rear_vehicle in traci.vehicle.getIDList():
        traci.vehicle.setMaxSpeed(rear_vehicle, 20)   # ~72 km/h
        current_edge = traci.vehicle.getRoadID(rear_vehicle)

        # Calculate trigger position only once
        if trigger_position is None and current_edge == target_edge_for_overtake:
            lane_id = traci.vehicle.getLaneID(rear_vehicle)
            lane_length = traci.lane.getLength(lane_id)
            trigger_position = lane_length * lane_position_fraction

        # Overtake condition
        if current_edge == target_edge_for_overtake and not overtaking:
            lane_pos = traci.vehicle.getLanePosition(rear_vehicle)
            if lane_pos >= trigger_position:
                leader_info = traci.vehicle.getLeader(rear_vehicle, overtake_distance_trigger)
                if leader_info:
                    leader_id, distance = leader_info
                    leader_speed = traci.vehicle.getSpeed(leader_id)

                    if leader_id == front_vehicle and leader_speed < traci.vehicle.getSpeed(rear_vehicle):
                        original_lane_index = traci.vehicle.getLaneIndex(rear_vehicle)
                        num_lanes = traci.edge.getLaneNumber(current_edge)
                        target_lane_index = (original_lane_index + 1) % num_lanes

                        traci.vehicle.setLaneChangeMode(rear_vehicle, 0b000000000000)
                        traci.vehicle.changeLane(rear_vehicle, target_lane_index, lanechange_duration)
                        print(f"{rear_vehicle} changed to lane {target_lane_index} to overtake {front_vehicle}")
                        overtaking = True

        # Return to lane condition
        elif overtaking and current_edge == target_edge_for_overtake:
            follower_info = traci.vehicle.getFollower(rear_vehicle, 100)
            if follower_info:
                follower_id, gap = follower_info
                if follower_id == front_vehicle and gap > safe_return_distance:
                    traci.vehicle.changeLane(rear_vehicle, original_lane_index, lanechange_duration)
                    print(f"{rear_vehicle} returned to lane {original_lane_index} ahead of {front_vehicle}")
                    overtaking = False

traci.close()
