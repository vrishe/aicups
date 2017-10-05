import sys

from strategy_utils import EnumBase


class _ElevatorConfigEnum(EnumBase):
	def __init__(self):
		self.__dict__['delay_operation']=40
		self.__dict__['duration_doors_close']=100
		self.__dict__['duration_doors_open']=100
		self.__dict__['passengers_avg']=10
		self.__dict__['passengers_max']=20
		self.__dict__['ticks_per_floor']=50
ElevatorConfig=_ElevatorConfigEnum()

class _ElevatorStateEnum(EnumBase):
	def __init__(self):
		self.__dict__['waiting']=0
		self.__dict__['moving']=1
		self.__dict__['opening']=2
		self.__dict__['filling']=3
		self.__dict__['closing']=4
ElevatorState=_ElevatorStateEnum()

class _GameConfigEnum(EnumBase):
	def __init__(self):
		self.__dict__['delay_enemy_invitation']=40
		self.__dict__['delay_passenger_spawn']=20
		self.__dict__['count_floors']=9
		self.__dict__['passenger_delivery_floor_cost']=10
		self.__dict__['passenger_delivery_enemy_mult']=2
		self.__dict__['duration_passenger_spawn']=2000
GameConfig=_GameConfigEnum()

class _PassengerStateEnum(EnumBase):
	def __init__(self):
		self.__dict__['waiting_for_elevator']=1
		self.__dict__['moving_to_elevator']=2
		self.__dict__['returning']=3
		self.__dict__['moving_to_floor']=4
		self.__dict__['using_elevator']=5
		self.__dict__['exiting']=6
PassengerState=_PassengerStateEnum()

class _PlayerTypeEnum(EnumBase):
	def __init__(self):
		self.__dict__['first']='FIRST_PLAYER'
		self.__dict__['second']='SECOND_PLAYER'
PlayerType=_PlayerTypeEnum()