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
	__rankings={}
	@staticmethod
	def assign_ranking(elevator, ranking=None):
		if not ranking:
			ranking=DistanceAssessmentElevatorController.__rankings.get(elevator.id)
		setattr(elevator, 'rank', ranking if ranking else 0)
		return elevator

	def run(self, strategy, elevator,
			my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		passenger_subject=next(
			itertools.ifilter(lambda p: p.ex.is_waiting(), my_passengers),
			None)
		if not passenger_subject:
			return

		elevators_without_rank=itertools.ifilter(
			lambda e: not e.rank, my_elevators)
		for elevator in elevators_without_rank:
			passenger_subject.set_elevator(elevator)
		elevator=passenger_subject.elevator
		rankings=DistanceAssessmentElevatorController.__rankings
		DistanceAssessmentElevatorController.assign_ranking(elevator,
			rankings.setdefault(elevator.id, len(rankings)+1))
		Timer.perform_next(
			lambda: strategy.switch_controller_by_name(
					elevator, 'PassengerLoadElevatorController')
				.run(strategy, elevator,
					my_elevators, my_passengers,
					enemy_elevators, enemy_passengers))


@ElevatorControllerBase.register
class FloorAnticipationMovementElevatorController(ElevatorControllerBase):
	def run(self, strategy, elevator,
			my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		pass	


@ElevatorControllerBase.register
class MovementElevatorController(ElevatorControllerBase):
	def run(self, strategy, elevator,
			my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		if elevator.state == ElevatorState.opening:
			if elevator.ex.get_ticks_passed() == 0:
				Timer.perform_delayed(
					ElevatorConfig.duration_doors_open,
					lambda: strategy.switch_controller_by_name(
							elevator, 'PassengerLoadElevatorController')
						.run(strategy, elevator, 
							my_elevators, my_passengers, 
							enemy_elevators, enemy_passengers))

		if elevator.state != ElevatorState.filling:
			return

		passenger=next(
			iter(sorted(
					elevator.passengers,
					key=lambda p: p.dest_floor-p.from_floor)),
			None)

		if passenger and passenger.dest_floor != elevator.next_floor:
			strategy.debug('Elevator #{} goes to {} floor with {} passengers on board.'
				.format(elevator.id, passenger.dest_floor, len(elevator.passengers)))
			elevator.go_to_floor(passenger.dest_floor)


@ElevatorControllerBase.register
class PassengerLoadElevatorController(ElevatorControllerBase):
	def __init__(self):
		self.passengers_incoming=[]
		self.distribution={
			1: (7,8),
			2: (6,7),
			3: (5,6,7),
			4: (3,4)
		}

	@staticmethod
	def is_incoming(passenger, elevator):
		return passenger.state == PassengerState.moving_to_elevator and passenger.elevator == elevator

	def run(self, strategy, elevator,
			my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		passengers_on_floor=itertools.ifilter(lambda p: p.from_floor==elevator.floor, 
			itertools.chain(my_passengers, enemy_passengers))
		if not passengers_on_floor:
			Timer.perform_next(
				lambda: strategy.switch_controller_by_name(
						elevator, 'FloorAnticipationMovementElevatorController'))
			return

		passengers_on_floor=sorted(passengers_on_floor, 
			key=lambda p: strategy.get_score_potential(p))
		passengers_map={ p.id:p for p in passengers_on_floor }
		self.passengers_incoming=filter(
			lambda pid: PassengerLoadElevatorController.is_incoming(passengers_map[pid], elevator),
			self.passengers_incoming)
		passengers_to_invite=itertools.ifilter(
			lambda p: p.ex.is_waiting_or_returning(), 
			passengers_on_floor)
		game_start=Timer.ticks <= GameConfig.duration_passenger_spawn
		chart=self.distribution[elevator.rank] if game_start else None
		for p in passengers_to_invite:
			travel=int(math.fabs(p.dest_floor-p.from_floor))
			if not chart or travel in chart:
				p.set_elevator(elevator)

		self.passengers_incoming.extend(map(
			lambda p: p.id,
			itertools.ifilter(lambda p: p.elevator == elevator, passengers_to_invite)))

		if game_start and len(elevator.passengers) < ElevatorConfig.passengers_max:
			return
		if self.passengers_incoming:
			return

		if elevator.passengers:
			Timer.perform_next(
				lambda: strategy.switch_controller_by_name(
						elevator, 'MovementElevatorController')
					.run(strategy, elevator, 
						my_elevators, my_passengers, 
						enemy_elevators, enemy_passengers))

## END REGION Controllers


class ElevatorEx(StateSentryBase):
	def __init__(self, timer):
		StateSentryBase.__init__(self, timer)

	# def can_invite_enemy_passenger(self):
	# 	return self.can_operate()	and self.get_ticks_passed() >= ElevatorConfig.delay_enemy_invitation
	# def can_operate(self):
	# 	return self.is_waiting() and self.get_ticks_passed() >= ElevatorConfig.delay_operation

	# def is_waiting(self):
	# 	return self.state == ElevatorState.waiting


class PassengerEx(StateSentryBase):
	def __init__(self, timer):
		StateSentryBase.__init__(self, timer)

	def is_waiting(self):
		return self.obj.state==PassengerState.waiting_for_elevator
	def is_waiting_or_returning(self):
		return self.obj.state==PassengerState.waiting_for_elevator or self.obj.state==PassengerState.returning


class Strategy(BaseStrategy):
	def __init__(self, debug, type):
		from strategy_utils import _DebugLogWrapper
		BaseStrategy.__init__(self, _DebugLogWrapper(debug), type)
		self.info=self.debug
		# must declare here for testing
		self.__ex=({}, {})

	#@timefunc
	def on_tick(self, my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		if Timer.ticks <= 0:
			raise Exception('Timer\'s got screwed up!')

		if Timer.ticks == 1:
			# First tick initialization
			self.__controllers={ 
				elevator.id: DistanceAssessmentElevatorController()
				for elevator in my_elevators
			}

		self.__update(my_elevators, my_passengers, 
			enemy_elevators, enemy_passengers)
		for elevator in my_elevators:
			self.__controllers[elevator.id].run(self, elevator,
				my_elevators, my_passengers, enemy_elevators, enemy_passengers)

		Timer.proceed_with_tick()

	def get_score_potential(self, passenger):
		result=GameConfig.passenger_delivery_floor_cost*math.fabs(passenger.dest_floor-passenger.from_floor)
		if (self.is_enemy(passenger)):
			result+=result
		return result

	def is_enemy(self, obj):
		return not self.is_my(obj)

	def is_my(self, obj):
		return obj.type == self.type

	def switch_controller_by_name(self, elevator, name):
		controller_old=self.__controllers.get(elevator.id, None)
		if type(controller_old).__name__==name:
			return controller_old	

		controller_new=ElevatorControllerBase.from_name(name)
		self.__controllers[elevator.id]=controller_new
		self.debug('Controllers switched for elevator #{}: {} -> {}'
			.format(elevator.id, type(controller_old).__name__, type(controller_new).__name__))
		return controller_new

	def __update(self, my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		for e in my_elevators:
			self.__ex[0].setdefault(e.id, ElevatorEx(Timer)).synchronize_with(
				DistanceAssessmentElevatorController.assign_ranking(e)) 
		for e in enemy_elevators:
			self.__ex[0].setdefault(e.id, ElevatorEx(Timer)).synchronize_with(e)
		for p in itertools.chain(my_passengers, enemy_passengers):
			self.__ex[1].setdefault(p.id, PassengerEx(Timer)).synchronize_with(p)


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

class DummyElevatorController(ElevatorControllerBase):
	def run(self, strategy, elevator,
			my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		if elevator.id == 2 and elevator.floor != 9 and elevator.state == ElevatorState.filling:
			elevator.go_to_floor(9)
		pass	


# Module tests below
if __name__ == '__main__':
	import sys

	def test_movement_elevator_controller_filling(args):
		import api
		from strategy_utils import _Timer
		controller=MovementElevatorController()
		elevator=api.Elevator('1',0,[],ElevatorState.filling,50,5,None,1000,'')
		elevator.passengers=[
			api.Passenger('1',elevator,0,0,PassengerState.using_elevator,39,5,8,'',5,1),
			api.Passenger('2',elevator,0,0,PassengerState.using_elevator,423,5,1,'',5,1),
		]
		strategy=Strategy(api.Debug(),'')
		strategy._Strategy__update([elevator],elevator.passengers,[],[])
		controller.run(strategy,elevator,[elevator],elevator.passengers,[],[])

	def test(args):
		from strategy_utils import _run_test_func
		_run_test_func(test_movement_elevator_controller_filling, args)

	sys.exit(test(sys.argv[1:]))