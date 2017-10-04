import bisect
import time


class ElevatorControllerBase(object):
	__controllers={}
	@classmethod
	def register(cls, subcls):
		cls.__controllers[subcls.__name__]=subcls
		return subcls
	@classmethod
	def from_name(cls, name, **kwargs):
		return cls.__controllers[name](**kwargs)

	def run(self, strategy, elevator,
			my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		pass

class StateSentryBase(object):
	def __init__(self, timer):
		self.obj=None
		self.__cb={}
		self.__t0=0
		self.__timer=timer

	def perform_on(state, action):
		self.__cb.setdefault(state, []).append(action)

	def synchronize_with(self, obj):
		setattr(obj, 'ex', self)
		if (not self.obj or self.obj.state != obj.state):
			self.obj=obj
			self.__t0=self.__timer.ticks
			for cb in self.__cb.pop(self.obj.state, []):
				cb(self)

	def get_ticks_passed(self):
		return self.__timer.ticks - self.__t0


class EnumBase(object):
	class EnumError(TypeError): pass
	def __setattr__(self,name,value):
			raise self.EnumError('Can\'t modify enum attribute: {}.'.format(name))


class _Timer(object):
	def __init__(self):
		self.__actions={}
		self.ticks=1

	def proceed_with_tick(self):
		for action in self.__actions.pop(self.ticks, []):
			action()
		self.ticks+=1

	def perform_at(self, tick, action):
		if tick < self.ticks:
			action()
			return

		self.__actions.setdefault(tick, []).append(action)

	def perform_delayed(self, ticks, action):
		self.perform_at(self.ticks+ticks, action)

	def perform_next(self, action):
		self.perform_at(self.ticks, action)

if __name__ != '__main__':
	Timer=_Timer()

	class _DebugLogWrapper(object):
		@staticmethod
		def write_line(text):
			print '{: >5}: {}'.format(Timer.ticks, text)
			pass

		def __init__(self, debug):
			self.debug_log=debug.log

		def log(self, text):
			_DebugLogWrapper.write_line(text)
			self.debug_log(text)


## @hidden

def timefunc(f):
	def f_timer(*args, **kwargs):
		start = time.time()
		try:
			return f(*args, **kwargs)
		finally:
			end = time.time()
			_DebugLogWrapper.write_line(
				'%s took %.3fs.' % (f.__name__, end - start))
		
	return f_timer


# Module tests below
def _run_test_func(f, args):
	f(args); print '{} passed'.format(f.__name__)

if __name__ == '__main__':
	import sys

	def test_timer(args):
		timer=_Timer()

		class _Counter(object):
			def __init__(self):
				self.value=0
			def increase(self):
				self.value=self.value+1

		counter=_Counter()
		timer.perform_at(0, counter.increase)
		assert timer.ticks == 1
		assert counter.value == 1

		timer.perform_at(1, counter.increase)
		timer.perform_at(1, counter.increase)
		timer.proceed_with_tick()
		assert timer.ticks == 2
		assert counter.value == 3

		timer.perform_at(2, counter.increase)
		timer.proceed_with_tick()
		assert timer.ticks == 3
		assert counter.value == 4

	def test_state_sentry_base(args):
		timer=_Timer()
		sentry=StateSentryBase(timer);

		assert not sentry.state

		class _ElevatorMock(object):
			def __init__(self):
				self.state=None
		elevator=_ElevatorMock()

		elevator.state=0
		sentry.synchronize_with(elevator)

		timer.proceed_with_tick()
		timer.proceed_with_tick()
		timer.proceed_with_tick()
		timer.proceed_with_tick()

		assert sentry.get_ticks_passed() == 4

		elevator.state=5
		sentry.synchronize_with(elevator)

		timer.proceed_with_tick()
		timer.proceed_with_tick()
		timer.proceed_with_tick()
		timer.proceed_with_tick()
		timer.proceed_with_tick()
		timer.proceed_with_tick()
		timer.proceed_with_tick()
		timer.proceed_with_tick()

		sentry.synchronize_with(elevator)
		assert sentry.get_ticks_passed() == 8

		elevator.state=2
		sentry.synchronize_with(elevator)
		assert sentry.get_ticks_passed() == 0

	def test_elevator_controller_base(args):
		controller=ElevatorControllerBase()

		@ElevatorControllerBase.register
		class _TestControllerA(ElevatorControllerBase): pass
		@ElevatorControllerBase.register
		class _TestControllerB(ElevatorControllerBase): pass

		assert len(ElevatorControllerBase.controllers) == 2
		assert ElevatorControllerBase.from_name('_TestControllerA').__class__ is _TestControllerA
		assert ElevatorControllerBase.from_name('_TestControllerB').__class__ is _TestControllerB

	def test(args):
		_run_test_func(test_timer, args)
		_run_test_func(test_state_sentry_base, args)
		_run_test_func(test_elevator_controller_base, args)

	sys.exit(test(sys.argv[1:]))