import itertools
import math

from strategy_constants import *
from strategy_utils import *
from base_strategy import BaseStrategy

if not 'timefunc' in dir():
	def timefunc(f): return f

## REGION Controllers

@ElevatorControllerBase.register
class DistanceAssessmentElevatorController(ElevatorControllerBase):
	def run(self, strategy, elevator,
			my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		my_passenger_waiting=next(
			itertools.ifilter(
				lambda p: p.state==PassengerState.waiting_for_elevator, 
				iter(my_passengers)),
			None)
		if not my_passenger_waiting:
			return

		elevators_unassigned=itertools.ifilter(
			lambda e: strategy.context.sentries[e.id].distance is None, 
			iter(my_elevators))
		for elevator in elevators_unassigned:
			my_passenger_waiting.set_elevator(elevator)
		elevator=my_passenger_waiting.elevator
		strategy.context.push_elevator(elevator)
		Timer.perform_next(
			lambda: strategy.switch_controller_by_name(
					elevator, 'BaselineElevatorController')
				.run(strategy, elevator, 
					my_elevators, my_passengers, 
					enemy_elevators, enemy_passengers))

## END REGION Controllers


## REGION Strategy context

class ElevatorStateSentry(ElevatorStateSentryBase):
	def __init__(self, timer):
		ElevatorStateSentryBase.__init__(self, timer)
		self.distance=None

	def is_waiting(self):
		return self.state == ElevatorState.waiting

	def can_invite_enemy_passenger(self):
		return self.can_operate()	and self.get_ticks_passed() >= ElevatorConfig.delay_enemy_invitation
	def can_operate(self):
		return self.is_waiting() and self.get_ticks_passed() >= ElevatorConfig.delay_operation


class StrategyContext(object):
	def __init__(self, strategy, elevators):
		self.__strategy=strategy
		self.elevators_order=[]
		self.sentries={ elevator.id: ElevatorStateSentry(Timer) 
			for elevator in elevators }

	def update(self, elevators):
		for elevator, sentry in map(lambda e: (e, self.sentries[e.id]), elevators):
			sentry.synchronize_with(elevator)

	def push_elevator(self, elevator):
		rank=len(self.elevators_order)
		self.sentries[elevator.id].distance=rank
		self.elevators_order.append(elevator.id)
		self.__strategy.debug('Elevator #{} assigned with rank {}'
			.format(elevator.id, rank))

## END REGION Strategy context


class Strategy(BaseStrategy):
	def __init__(self, debug, type):
		from strategy_utils import _DebugLogWrapper
		BaseStrategy.__init__(self, _DebugLogWrapper(debug), type)

	#@timefunc
	def on_tick(self, my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		if Timer.ticks <= 0:
			return

		elevators=itertools.chain(my_elevators, enemy_elevators)

		if Timer.ticks == 1:
			# First tick initialization
			self.__controllers={ elevator.id: DistanceAssessmentElevatorController() 
				for elevator in my_elevators }
			self.context=StrategyContext(self, elevators)

		self.context.update(elevators)
		for elevator in my_elevators:
			self.__controllers[elevator.id].run(self, elevator,
				my_elevators, my_passengers, enemy_elevators, enemy_passengers)

		Timer.proceed_with_tick()

	def is_enemy(self, obj):
		return not self.is_my(obj)

	def is_my(self, obj):
		return obj.type == self.type

	def get_score_potential(self, passenger):
		floorDelta=math.fabs(passenger.dest_floor-passenger.from_floor)
		if (self.is_enemy(passenger)):
			return PassengerFloorCost.enemy*floorDelta
		return PassengerFloorCost.my*floorDelta

	def switch_controller_by_name(self, elevator, name):
		controller_old=self.__controllers.get(elevator.id, None)
		controller_new=ElevatorControllerBase.from_name(name)
		self.__controllers[elevator.id]=controller_new
		self.debug('Controllers switched for elevator #{}: {} -> {}'.format(elevator.id, type(controller_old).__name__, type(controller_new).__name__))
		return controller_new


## @hidden

@ElevatorControllerBase.register
class BaselineElevatorController(ElevatorControllerBase):
	def run(self, strategy, elevator,
			my_elevators, my_passengers, enemy_elevators, enemy_passengers): 
		passengers = [p for p in my_passengers if p.state < 5]
		for p in passengers:
			if elevator.state != 1:
				elevator.go_to_floor(p.from_floor)
			if elevator.floor == p.from_floor:
				p.set_elevator(elevator)
		if len(elevator.passengers) > 0 and elevator.state != 1:
			elevator.go_to_floor(elevator.passengers[0].dest_floor)

# Module tests below
if __name__ == '__main__':
	import api, sys

	def test_strategy_context(args):
		elevators=[ 
			api.Elevator(0, 0, [], 'waiting', 50, 0, None, 0, 'FIRST_PLAYER'),
			api.Elevator(1, 0, [], 'waiting', 50, 0, None, 0, 'FIRST_PLAYER')
		]
		context=StrategyContext(api.Debug(), Timer(), elevators)

		print 'test_strategy_context passed'

	def debug_stub(str):
		pass

	def test(args):
		test_strategy_context(args)

	sys.exit(test(sys.argv[1:]))