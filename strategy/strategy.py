import math

from strategy_constants import PassengerFloorCost
from strategy_constants import PlayerType
from core.base_strategy import BaseStrategy


FLOOR_COST_MAPPING = {
    PlayerType.first: PassengerFloorCost.my,
    PlayerType.second: PassengerFloorCost.enemy
}

class Strategy(BaseStrategy):
    def on_tick(self, my_elevators, my_passengers, enemy_elevators, enemy_passengers):
        for elevator in my_elevators:
            passengers = [p for p in my_passengers if p.state < 5]
            for p in passengers:
                if elevator.state != 1:
                    elevator.go_to_floor(p.from_floor)
                if elevator.floor == p.from_floor:
                    p.set_elevator(elevator)
            if len(elevator.passengers) > 0 and elevator.state != 1:
                elevator.go_to_floor(elevator.passengers[0].dest_floor)

def scoring_potential(passenger):
    return FLOOR_COST_MAPPING[passenger.type]*math.fabs(passenger.dest_floor-passenger.from_floor)



