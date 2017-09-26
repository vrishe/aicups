import sys

from strategy_utils import EnumBase


class _PlayerTypeEnum(EnumBase):
	def __init__(self):
		self.__dict__['first']='FIRST_PLAYER'
		self.__dict__['second']='SECOND_PLAYER'
PlayerType=_PlayerTypeEnum()


class _PassengerFloorCostEnum(EnumBase):
	def __init__(self):
		self.__dict__['my']=10
		self.__dict__['enemy']=20
PassengerFloorCost=_PassengerFloorCostEnum()