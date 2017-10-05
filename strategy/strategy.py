import bisect
import itertools
import math

from strategy_constants import *
from strategy_utils import *
from base_strategy import BaseStrategy


if not 'timefunc' in dir():
	def timefunc(f): return f


## REGION Controllers

@ElevatorControllerBase.register
class AnticipatedMovementElevatorController(ElevatorControllerBase):
	def run(self, strategy, elevator,
		my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		direction_preferred=0
		for passenger in elevator.passengers:
			direction_preferred+=passenger.dest_floor-elevator.floor
		floor_selected=None

		passengers=iter(my_passengers)
		if elevator.ex.can_invite_enemy():
			passengers=itertools.chain(passengers, enemy_passengers)
		for floor in range(1, GameConfig.count_floors):
			passengers_on_floor=itertools.ifilter(
				lambda p: p.floor==floor, passengers)
			if not passengers_on_floor:
				continue

		if floor_selected!=elevator.floor:
			PassengerLoadElevatorController.send_elevator_to_floor(
				strategy, elevator, floor_selected)


@ElevatorControllerBase.register
class EarlyPassengerLoadElevatorController(ElevatorControllerBase):
	timeout_departure=150

	def __init__(self):
		self.reset_timeout()

	def reset_timeout(self):
		self.__timeout=EarlyPassengerLoadElevatorController.timeout_departure

	def run(self, strategy, elevator,
			my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		assert elevator.ex.is_filling(), 'Elevator #{} is not filling!'.format(elevator.id)

		self.__timeout-=1
		if self.__timeout<=(40*(4-elevator.rank)) or elevator.ex.is_full():
			PassengerLoadElevatorController.send_elevator_to_floor(strategy, elevator,
				elevator.passengers[0].dest_floor if elevator.passengers else 0)
			return

		passengers=iter(my_passengers)
		if elevator.ex.can_invite_enemy():
			passengers=itertools.chain(passengers, enemy_passengers)
		passengers_on_floor=itertools.ifilter(
			lambda p: p.floor==elevator.floor, passengers)

		if any(itertools.ifilter(
			lambda p: p.ex.may_be_invited() or p.ex.is_moving_to(elevator), 
			passengers_on_floor)):
				self.reset_timeout()

		if not strategy.may_spawn():
			return

		invitation_queue=itertools.ifilter(
			lambda p: GameConfig.count_floors-elevator.rank==p.ex.get_travel_distance(),
			sorted(itertools.ifilter(
					lambda p: p.ex.may_be_invited(), 
					passengers_on_floor), 
				key=lambda p: p.dest_floor, 
				reverse=True))
		for passenger in invitation_queue:
			passenger.set_elevator(elevator)
			passenger.ex.perform_on(PassengerState.waiting_for_elevator,
				lambda passenger_ex: strategy.debug('Passenger #{} is on {} floor, next goes to {} floor.'.format(passenger_ex.obj.id, passenger_ex.obj.floor, passenger_ex.obj.dest_floor)))


@ElevatorControllerBase.register
class NoOpElevatorController(ElevatorControllerBase):
	pass


@ElevatorControllerBase.register
class PassengerLoadElevatorController(ElevatorControllerBase):

	@staticmethod
	def send_elevator_to_floor(strategy, elevator, floor):
		if floor:
			strategy.info('Elevator #{} is sent to {} foor'.format(elevator.id, floor))
			elevator.go_to_floor(floor)
		strategy.switch_controller_by_name(
			elevator, 'NoOpElevatorController')
		elevator.ex.perform_on(ElevatorState.filling, 
			lambda elevator_ex: strategy.switch_controller_by_name(
				elevator_ex.obj, 'PassengerLoadElevatorController'))

	def run(self, strategy, elevator,
			my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		assert elevator.ex.is_filling(), 'Elevator #{} is not filling!'.format(elevator.id)

		if elevator.ex.is_full():
			PassengerLoadElevatorController.send_elevator_to_floor(
				strategy, elevator,
				sorted(elevator.passengers, 
					key=lambda p: p.dest_floor, reverse=True)[0].dest_floor)

		passengers=iter(my_passengers)
		if elevator.ex.can_invite_enemy():
			passengers=itertools.chain(passengers, enemy_passengers)
		my_elevators_map={e.id:e for e in my_elevators}
		passengers_on_floor=sorted(
			itertools.ifilter(
				lambda p: p.floor==elevator.floor and (p.ex.may_be_invited() or my_elevators_map.get(p.ex.get_elevator_id(), elevator).rank>elevator.rank),
				passengers), 
			key=lambda p: strategy.get_score_potential(p), 
			reverse=True)
		if not passengers_on_floor:
			# strategy.switch_controller_by_name(
			# 	elevator, 'AnticipatedMovementElevatorController').run(
			# 		strategy, elevator, my_elevators, my_passengers,
			# 			enemy_elevators, enemy_passengers)
			return
		strategy.info('There are {} passengers to invite.'.format(len(passengers_on_floor)))
		dest_floor_last=passengers_on_floor[0].dest_floor
		for passenger in passengers_on_floor:
			if dest_floor_last!=passenger.dest_floor:
				break
			strategy.info('Elevator #{} invites Passenger #{} with {} potential score'.format(elevator.id, passenger.id, strategy.get_score_potential(passenger)))
			passenger.set_elevator(elevator)


@ElevatorControllerBase.register
class RankingElevatorController(ElevatorControllerBase):
	__rankings={}
	@staticmethod
	def assign_ranking(elevator, ranking=None):
		if not ranking:
			ranking=RankingElevatorController.__rankings.get(elevator.id)
		setattr(elevator, 'rank', ranking if ranking else 0)
		return elevator

	@staticmethod
	def specify_ranking(strategy, elevator, ranking=None):
		rankings=RankingElevatorController.__rankings
		if not ranking:
			ranking=len(rankings)+1
		location=60+(ranking-1)*80
		elevator.ex.x=-location if elevator.type==PlayerType.first else location
		RankingElevatorController.assign_ranking(elevator, 
			rankings.setdefault(elevator.id, ranking))
		Timer.perform_next(
			lambda: strategy.switch_controller_by_name(
					elevator, 'EarlyPassengerLoadElevatorController'))
		strategy.info('Elevator #{} is assigned with ranking {}'.format(elevator.id, elevator.rank))

	@staticmethod
	def infer_ranking(strategy, elevator, my_elevators):
		rankings=[]
		for e in my_elevators:
			if e.rank:
				bisect.insort(rankings, e.rank)
		if len(rankings)!=len(my_elevators)-1:
			return False

		rank_new=1
		for rank in rankings:
			if rank==rank_new:
				rank_new+=1
		RankingElevatorController.specify_ranking(strategy, elevator, rank_new)
		return True

	@staticmethod
	def on_passenger_state_changed(strategy, elevator, passenger):
		if passenger.elevator==elevator.id: 
			RankingElevatorController.specify_ranking(strategy, elevator)

	def __init__(self):
		self.passenger_ex=None

	def run(self, strategy, elevator,
			my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		if self.passenger_ex and self.passenger_ex.obj.elevator==elevator.id:
			return
		if RankingElevatorController.infer_ranking(strategy, elevator, my_elevators):
			return

		passengers=iter(my_passengers)
		if elevator.ex.can_invite_enemy():
			passengers=itertools.chain(passengers, enemy_passengers)
		passenger=next(itertools.ifilter(
			lambda p: p.floor==elevator.floor and p.ex.may_be_invited() and not p.ex.get_elevator_id() in (e.id for e in my_elevators), 
			passengers), 
		None)
		del passengers
		if not passenger:
			return

		passenger.set_elevator(elevator)
		elevator_ex=elevator.ex
		
		self.passenger_ex=passenger.ex
		self.passenger_ex.perform_on(PassengerState.using_elevator, 
			lambda passenger_ex: RankingElevatorController.on_passenger_state_changed(
				strategy, elevator_ex.obj, passenger_ex.obj))

## END REGION Controllers


class ElevatorEx(StateSentryBase):
	def __init__(self, timer):
		StateSentryBase.__init__(self, timer)
		self.x=None

	def can_invite_enemy(self):
		return self.get_ticks_passed()>=GameConfig.delay_enemy_invitation
	def can_operate(self):
		return self.obj.state==ElevatorState.filling and self.get_ticks_passed()>=ElevatorConfig.delay_operation
	def get_ticks_to_reach_floor(self, floor):
		if self.obj.floor==floor:
			return 0
		ticks_per_floor=ElevatorConfig.ticks_per_floor
		for passenger in elevator.passengers:
			ticks_per_floor*=passenger.weight
		if len(elevator.passengers)>ElevatorConfig.passengers_avg:
			ticks_per_floor*=1.1
		return int(math.fabs(self.obj.floor-floor))*ticks_per_floor
	def has_overload(self):
		return len(self.obj.passengers)>ElevatorConfig.passengers_avg
	def is_filling(self):
		return self.obj.state==ElevatorState.filling
	def is_full(self):
		return len(self.obj.passengers)>=ElevatorConfig.passengers_max

	def track_x(passenger_ex):
		self.x=passenger_ex.obj.x


class PassengerEx(StateSentryBase):
	def __init__(self, timer):
		StateSentryBase.__init__(self, timer)

	def get_elevator_id(self):
		if self.obj.elevator is None:
			return None
		if type(self.obj.elevator) is int:
			return self.obj.elevator
		return self.obj.elevator.id
	def get_travel_direction(self):
		return self.obj.dest_floor-self.obj.from_floor
	def get_travel_distance(self):
		return int(math.fabs(self.get_travel_direction()))
	def is_moving_to(self, elevator):
		return self.obj.state==PassengerState.moving_to_elevator and self.get_elevator_id()==elevator.id
	def is_waiting(self):
		return self.obj.state==PassengerState.waiting_for_elevator
	def is_waiting_or_returning(self):
		return self.obj.state==PassengerState.waiting_for_elevator or self.obj.state==PassengerState.returning
	def may_be_invited(self):
		return self.is_waiting_or_returning()


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
				elevator.id: RankingElevatorController()
				for elevator in my_elevators
			}

		self.__update(my_elevators, my_passengers, 
			enemy_elevators, enemy_passengers)
		for elevator in sorted(my_elevators, key=lambda e: e.rank, reverse=True):
			self.__controllers[elevator.id].run(self, elevator,
				my_elevators, my_passengers, enemy_elevators, enemy_passengers)

		Timer.proceed_with_tick()

	def get_score_potential(self, passenger):
		result=passenger.ex.get_travel_distance()*GameConfig.passenger_delivery_floor_cost
		if (self.is_enemy(passenger)):
			result*=GameConfig.passenger_delivery_enemy_mult
		return result

	def is_enemy(self, obj):
		return not obj is None and obj.type != self.type
	def is_my(self, obj):
		return not obj is None and obj.type == self.type
	def may_spawn(self):
		return Timer.ticks<GameConfig.duration_passenger_spawn

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
				RankingElevatorController.assign_ranking(e)) 
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

# Module tests below
if __name__ == '__main__':
	import sys

	def test_infer_ranking(args):
		import api
		strategy=Strategy(api.Debug(), PlayerType.second)
		class ElevatorMock(object):
			def __init__(self, id, type, rank):
				self.id=id
				self.type=type
				self.rank=rank
				self.ex=ElevatorEx(Timer)

		elevators=[
			ElevatorMock(1, PlayerType.first, 4),
			ElevatorMock(2, PlayerType.first, 2),
			ElevatorMock(3, PlayerType.first, 1),
			ElevatorMock(4, PlayerType.first, None),
		]
		assert RankingElevatorController.infer_ranking(strategy, elevators[3], elevators) is True
		assert elevators[3].rank==3
		assert elevators[3].ex.x==-220

		elevators=[
			ElevatorMock(1, PlayerType.second, 2),
			ElevatorMock(2, PlayerType.second, 1),
			ElevatorMock(3, PlayerType.second, None),
			ElevatorMock(4, PlayerType.second, 4),
		]
		assert RankingElevatorController.infer_ranking(strategy, elevators[2], elevators) is True
		assert elevators[2].rank==3
		assert elevators[2].ex.x==220

		elevators=[
			ElevatorMock(1, PlayerType.second, None),
			ElevatorMock(2, PlayerType.second, 3),
			ElevatorMock(3, PlayerType.second, 1),
			ElevatorMock(4, PlayerType.second, 2),
		]
		assert RankingElevatorController.infer_ranking(strategy, elevators[1], elevators) is True
		assert elevators[1].rank==4
		assert elevators[1].ex.x==300

		elevators=[
			ElevatorMock(1, PlayerType.second, None),
			ElevatorMock(2, PlayerType.second, None),
			ElevatorMock(3, PlayerType.second, None),
			ElevatorMock(4, PlayerType.second, None),
		]
		assert RankingElevatorController.infer_ranking(strategy, elevators[1], elevators) is False


	def test(args):
		from strategy_utils import _run_test_func
		_run_test_func(test_infer_ranking, args)

	sys.exit(test(sys.argv[1:]))