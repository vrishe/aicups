import bisect
import time


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


class ElevatorControllerBase(object):
	controllers={}
	@classmethod
	def register(cls, subcls):
		cls.controllers[subcls.__name__]=subcls
		return subcls
	@classmethod
	def from_name(cls, name, **kwargs):
		return cls.controllers[name](**kwargs)

	def run(self, strategy, elevator,
			my_elevators, my_passengers, enemy_elevators, enemy_passengers):
		pass


class EnumBase(object):
	class EnumError(TypeError): pass
	def __setattr__(self,name,value):
			raise self.EnumError('Can\'t modify enum attribute: {}.'.format(name))


class StateSentryBase(object):
	def __init__(self, timer):
		self.obj=None
		self.__cb={}
		self.__state=None
		self.__t0=0
		self.__timer=timer

	def perform_on(self, state, action):
		self.__cb.setdefault(state, []).append(action)
	def remove_callbacks(self, state, action=None):
		actions=self.__cb.get(state, [])
		if action:
			actions.remove(action)
		if not action or not actions:
			del self.__cb[state]

	def synchronize_with(self, obj):
		self.obj=obj
		setattr(obj, 'ex', self)
		if self.__state!=obj.state:
			self.__state=obj.state
			self.__t0=self.__timer.ticks
			for cb in self.__cb.pop(obj.state, []):
				cb(self)

	def get_ticks_passed(self):
		return self.__timer.ticks-self.__t0


class StateGraph(object):
	class Node(object):
		def __init__(self, state, value, children, parent=None):
			self.children=children
			self.parent=parent
			self.state=state
			self.value=value

	class Builder(object):
		def __init__(self):
			self.__tree_map={}

		def add(self, state, value, *args):
			if state in self.__tree_map:
				raise Exception('State {} is already present.'.format(state))
			self.__tree_map[state]=(len(self.__tree_map), StateGraph.Node(state, value, list(args)))
			return self

		def build(self, root_state=None):
			for i, node in self.__tree_map.itervalues():
				if i==0:
					first=node
				children=[]
				for child in node.children:
					child=self.__tree_map.get(child)
					if child is not None:
						child=child[1]
						if child.parent is not None:
							raise Exception('Child with state {} has a parent already.'.format(child.state))
						child.parent=node
						children.append(child)
				node.children=children
			return StateGraph(self.__tree_map[root_state] if root_state is not None else first)

	def __init__(self, root):
		self.root=root

	def find_path(self, state_to, state_from=None):
		src=self.root if state_from is None else self.get(state_from)
		dst=self.get(state_to)
		if src is not None and dst is not None:
			if dst is src:
				return []
			path=[]
			while dst is not src:
				path.insert(0, dst)
				dst=dst.parent
				if dst is None:
					return []
			path.insert(0, src)
			return path
		return None

	def get(self, state):
		nodes=[self.root]
		while nodes:
			node=nodes.pop()
			if node.state==state:
				return node
			nodes.extend(node.children)
		return None


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


	def test_state_graph_builder_add_throws(args):
		try:
			StateGraph.Builder().add(
				'state_a', 0, 'state_b').add(
				'state_a', 2, 'state_b', 'state_c').add(
				'state_c', 3, 'state_a').build()
			assert False
		except:
			pass

	def test_state_graph_builder_build_throws(args):
		try:
			StateGraph.Builder().add(
				'state_a', 0, 'state_b').add(
				'state_b', 2, 'state_c', 'state_b').add(
				'state_c', 3, 'state_a').build()
			assert False
		except:
			pass

	def test_state_graph_find_path(args):
		graph=StateGraph.Builder().add(
			'a', 0, 'b', 'c').add(
			'b', 2).add(
			'c', 3, 'd').add(
			'd', 12, 'e', 'f').add(
			'e', 5).add(
			'f', 7).build()

		path=graph.find_path('f')
		assert len(path)==4 and all(map(lambda t: t[0].state==t[1], zip(path, ['a','c','d','f'])))

		path=graph.find_path('f', state_from='b')
		assert not path and path is not None

	def test_state_graph_get(args):
		graph=StateGraph.Builder().add(
			'state_a', 0, 'state_b').add(
			'state_b', 2, 'state_c').add(
			'state_c', 3, 'state_a').build()
		node=graph.get('state_b')
		assert node.parent.state=='state_a'
		assert len(node.children)==1 and node.children[0].state=='state_c'


	def test_state_sentry_base(args):
		timer=_Timer()
		sentry=StateSentryBase(timer);

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
		_run_test_func(test_state_graph_builder_add_throws, args)
		_run_test_func(test_state_graph_builder_build_throws, args)
		_run_test_func(test_state_graph_find_path, args)
		_run_test_func(test_state_graph_get, args)
		_run_test_func(test_state_sentry_base, args)
		_run_test_func(test_elevator_controller_base, args)

	sys.exit(test(sys.argv[1:]))