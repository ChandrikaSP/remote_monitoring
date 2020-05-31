import inflection

from uuid import generate_uuid
from datasets import flatten_dict, keep_entry

attributes = ['position', 'availability', 'component_status', 'schedule', 'current_task',
              'version']


class Robot(object):
    def __init__(self, robot_id, uuid=None, **kwargs):
        self.robot_id = robot_id

        if uuid is None:
            self.uuid = generate_uuid()
        else:
            self.uuid = uuid

        self.last_update = dict()

        self.position = kwargs.get('position', None)
        self.availability = kwargs.get('availability', None)
        self.component_status = kwargs.get('component_status', None)
        self.schedule = kwargs.get('schedule', None)
        self.current_task = kwargs.get('current_task', None)

        self.nickname = kwargs.get('nickname', None)

        self.version = kwargs.get('version', {'hardware': Hardware.full_version(),
                                              'software': Software.full_version(),
                                              'black_box': BlackBox.full_version()})

        for attr in attributes:
            val = self.__dict__.get('attr', None)
            if val is not None:
                self.last_update[attr] = val

    def to_dict(self):
        robot_dict = dict()

        for k, v in self.__dict__.items():
            key = inflection.camelize(k, False)
            robot_dict[key] = v

        return robot_dict

    @staticmethod
    def from_dict(robot_dict):
        robot = Robot(robot_dict['robotId'])
        robot.schedule = robot_dict['schedule']
        robot.nickname = robot_dict.get('nickname', None)
        robot.uuid = robot_dict.get('uuid')
        robot.version = robot_dict.get('version')
        robot.position = robot_dict.get('position')
        return robot

    @staticmethod
    def to_csv(robot_dict):
        """ Prepares dict to be written to a csv
        :return: dict
        """
        flattened_dict = flatten_dict(robot_dict)
        to_csv_dict = keep_entry(flattened_dict, 'status', ['status'])

        return to_csv_dict


class Hardware(object):
    @staticmethod
    def wheel(wheel_id, serial='unknown', firmware_version='unknown'):
        return {'id': wheel_id, 'serial_number': serial, 'firmware_version': firmware_version}

    @staticmethod
    def sensor_cube(cube_id, serial='unknown', firmware_version='unknown'):
        return {'id': cube_id, 'serial_number': serial, 'firmware_version': firmware_version}

    @staticmethod
    def laser(model='Hokuyo', serial='unknown'):
        return {'model': model, 'serial_number': serial}

    @staticmethod
    def ropod_hw(serial='unknown', firmware='unknown'):
        return {'serial_number': serial, 'firmware_version': firmware}

    @staticmethod
    def full_version(wheels=None, laser=None, sensor_cubes=None, docking_mechanism=None):
        if wheels is None:
            wheels = [Hardware.wheel(i) for i in range(1, 5)]
        if laser is None:
            laser = Hardware.laser()
        if sensor_cubes is None:
            sensor_cubes = [Hardware.sensor_cube(i) for i in range(1, 2)]
        if docking_mechanism is None:
            docking_mechanism = Hardware.ropod_hw()

        return {'wheels': wheels,
                'laser': laser,
                'sensor_cubes': sensor_cubes,
                'docking_mechanism': docking_mechanism}


class Software(object):
    @staticmethod
    def community_pkg(pkg, version='unknown'):
        return {'package': pkg, 'version': version}

    @staticmethod
    def ropod_sw(version='unknown'):
        return {'version': version}

    @staticmethod
    def navigation_sw(route_navigation=None, maneuver_navigation=None, local_planner=None, localization=None):
        if route_navigation is None:
            route_navigation = Software.ropod_sw()
        if maneuver_navigation is None:
            maneuver_navigation = Software.ropod_sw()
        if local_planner is None:
            local_planner = Software.community_pkg('teb', '0.6.11')
        if localization is None:
            localization = Software.community_pkg('amcl', '1.14.4')
        route_planner = Software.ropod_sw()
        map_server = Software.community_pkg('map_server', '1.14.4')
        map_switcher = Software.ropod_sw()
        floor_detection = Software.ropod_sw()
        door_status_detection = Software.ropod_sw()

        return {'route_navigation': route_navigation,
                'maneuver_navigation': maneuver_navigation,
                'local_planner': local_planner,
                'map_server': map_server,
                'map_switcher': map_switcher,
                'floor_detection': floor_detection,
                'door_status_detection': door_status_detection,
                'route_planner': route_planner,
                'localization': localization}

    @staticmethod
    def world_model_sw(ed=None, osm=None, overpass=None, wm_mediator=None, osm_ros=None):
        if ed is None:
            ed = Software.community_pkg('ed')
        if osm is None:
            osm = Software.ropod_sw()
        if overpass is None:
            overpass = Software.ropod_sw()
        if wm_mediator is None:
            wm_mediator = Software.ropod_sw()
        if osm_ros is None:
            osm_ros = Software.ropod_sw()

        return {'ed': ed, 'osm_bridge': osm, 'overpass': overpass, 'wm_mediator': wm_mediator,
                'osm_bridge_ros_wrapper': osm_ros}

    @staticmethod
    def full_version(navigation=None, world_model=None, communication_mediator=None, task_execution=None):
        if navigation is None:
            navigation = Software.navigation_sw()
        if world_model is None:
            world_model = Software.world_model_sw()
        if communication_mediator is None:
            communication_mediator = Software.ropod_sw()
        if task_execution is None:
            task_execution = Software.ropod_sw()

        interfaces = {'sound_communicator': Software.ropod_sw(),
                      'joypad': Software.ropod_sw()}
        diagnosis = {'component_monitoring': Software.ropod_sw(),
                     'experiment_executor': Software.ropod_sw()}
        communication = {'com_mediator': communication_mediator}
        execution = {'execution': task_execution}

        return {'communication': communication,
                'navigation': navigation,
                'world_model': world_model,
                'execution': execution,
                'interfaces': interfaces,
                'diagnosis': diagnosis}


class BlackBox(object):
    @staticmethod
    def full_version(uuid=None):
        if uuid is None:
            uuid = generate_uuid()
        return {'uuid': uuid, 'logger': Software.ropod_sw(), 'fault_detection': Software.ropod_sw()}
