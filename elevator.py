import inflection


class ElevatorRequests(object):
    def __init__(self):
        self.current_floor = -1
        self.number_of_active_requests = -1


class ElevatorRequestStatus:
    PENDING = 0
    ACCEPTED = 8
    GOING_TO_START = 1
    WAITING_FOR_ROBOT_IN = 2
    GOING_TO_GOAL = 3
    WAITING_FOR_ROBOT_OUT = 4
    COMPLETED = 5
    CANCELED = 6
    FAILED = 7


class ElevatorRequest(object):

    def __init__(self, query_id, start_floor, goal_floor, command, elevator_id=1, **kwargs):

        self.query_id = query_id
        self.command = command
        self.elevator_id = elevator_id
        self.start_floor = start_floor
        self.goal_floor = goal_floor
        self.operational_mode = kwargs.get('mode', 'ROBOT')

        self.task_id = kwargs.get('task_id', None)
        self.load = kwargs.get('load', None)
        self.robot_id = kwargs.get('robot_id', None)
        self.status = ElevatorRequestStatus.PENDING

    def to_dict(self):
        request_dict = dict()
        request_dict['elevatorId'] = self.elevator_id
        request_dict['operationalMode'] = self.operational_mode
        request_dict['startFloor'] = self.start_floor
        request_dict['goalFloor'] = self.goal_floor
        request_dict['queryId'] = self.query_id
        request_dict['command'] = self.command
        request_dict['load'] = self.load
        request_dict['robotId'] = self.robot_id
        request_dict['status'] = self.status
        request_dict['taskId'] = self.task_id
        return request_dict

    @staticmethod
    def from_dict(request):
        query_id = request['queryId']
        command = request['command']
        start_floor = request['startFloor']
        goal_floor = request['goalFloor']
        elevator_id = request.get('elevatorId')

        robot_request = ElevatorRequest(query_id, start_floor, goal_floor, command, elevator_id)

        robot_request.task_id = request.get('taskId')
        robot_request.load = request.get('load')
        robot_request.robot_id = request.get('robotId')
        robot_request.status = request.get('status', ElevatorRequestStatus.PENDING)
        return robot_request

    def __str__(self):
        return "ElevatorRequest(query_id=%s, command=%s, start_floor=%s, goal_floor=%s, elevator_id=%s, task_id=%s, " \
               "load=%s, robot_id=%s, status=%s)" % (self.query_id, self.command, self.start_floor, self.goal_floor,
                                                     self.elevator_id, self.task_id, self.load, self.robot_id,
                                                     self.status)


class Elevator(object):

    def __init__(self, elevator_id):
        self.elevator_id = elevator_id
        self.floor = -1 # TODO: Need to match floors from toma messages to world model ones
        self.calls = -1
        self.is_available = False
        self.door_open_at_goal_floor = False
        self.door_open_at_start_floor = False

    def to_dict(self):
        elevator_dict = dict()
        elevator_dict['elevatorId'] = self.elevator_id
        elevator_dict['floor'] = self.floor
        elevator_dict['calls'] = self.calls
        elevator_dict['isAvailable'] = self.is_available
        elevator_dict['doorOpenAtGoalFloor'] = self.door_open_at_goal_floor
        elevator_dict['doorOpenAtStartFloor'] = self.door_open_at_start_floor
        return elevator_dict

    @staticmethod
    def from_dict(elevator_dict):
        elevator = Elevator(elevator_dict['elevatorId'])
        elevator.elevator_id = elevator_dict['elevatorId']
        elevator.floor = elevator_dict['floor']
        elevator.calls = elevator_dict['calls']
        elevator.is_available = elevator_dict['isAvailable']
        elevator.door_open_at_goal_floor = elevator_dict['doorOpenAtGoalFloor']
        elevator.door_open_at_start_floor = elevator_dict['doorOpenAtStartFloor']
        return elevator

    def update(self, status):
        for k, v in status.items():
            if k != 'metamodel':
                key = inflection.underscore(k)
                self.__dict__[key] = v

    def at_goal_floor(self):
        if self.door_open_at_goal_floor:
            return True
        else:
            return False

    def at_start_floor(self):
        if self.door_open_at_start_floor:
            return True
        else:
            return False


class RobotCallUpdate(object):
    def __init__(self, query_id, command, elevator_id=1, start_floor=None, goal_floor=None):
        self.queryId = query_id
        self.command = command
        self.elevatorId = elevator_id
        if start_floor:
            self.startFloor = start_floor
        elif goal_floor:
            self.goalFloor = goal_floor
        else:
            raise Exception("Missing goal or start floor")

    def to_dict(self):
        return self.__dict__

    @property
    def meta_model(self):
        return 'robot-call-update'


class RobotElevatorCallReply(object):
    def __init__(self, query_id, query_success=True, elevator_id=1, elevator_waypoint='door-1'):
        self.queryId = query_id
        self.querySuccess = query_success
        self.elevatorId = elevator_id
        self.elevatorWaypoint = elevator_waypoint

    def to_dict(self):
        return self.__dict__

    @property
    def meta_model(self):
        return 'robot-elevator-call-reply'