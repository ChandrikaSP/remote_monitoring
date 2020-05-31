from __future__ import print_function
import json
import uuid
import threading

from flask import Blueprint, render_template, jsonify, request, session
from flask_socketio import emit

from data_utils import DataUtils

from common import socketio, Config
from black_box_utils import BBUtils

# variables to be queried
wheel_vars = ['ros_sw_ethercat_parser_data/sensors/*/current_1_q',
              'ros_sw_ethercat_parser_data/sensors/*/current_2_q',
              'ros_sw_ethercat_parser_data/sensors/*/voltage_1',
              'ros_sw_ethercat_parser_data/sensors/*/voltage_2',
              'ros_sw_ethercat_parser_data/sensors/*/velocity_1',
              'ros_sw_ethercat_parser_data/sensors/*/velocity_2',
              'ros_sw_ethercat_parser_data/sensors/*/velocity_pivot',
              'ros_sw_ethercat_parser_data/sensors/*/temperature_1',
              'ros_sw_ethercat_parser_data/sensors/*/temperature_2',
              'ros_sw_ethercat_parser_data/sensors/*/accel_x',
              'ros_sw_ethercat_parser_data/sensors/*/accel_y',
              'ros_sw_ethercat_parser_data/sensors/*/accel_z',
              'ros_sw_ethercat_parser_data/sensors/*/gyro_x',
              'ros_sw_ethercat_parser_data/sensors/*/gyro_y',
              'ros_sw_ethercat_parser_data/sensors/*/gyro_z',
              'ros_sw_ethercat_parser_data/sensors/*/pressure']

cmd_vel_vars = ['ros_ropod_cmd_vel/linear/x',
                'ros_ropod_cmd_vel/linear/y',
                'ros_ropod_cmd_vel/angular/z']


# short names of the variables to be queried
wheel_var_name_mapping = {
    'ros_sw_ethercat_parser_data/sensors/*/current_1_q': 'I_1_q',
    'ros_sw_ethercat_parser_data/sensors/*/current_2_q': 'I_2_q',
    'ros_sw_ethercat_parser_data/sensors/*/voltage_1': 'V_1',
    'ros_sw_ethercat_parser_data/sensors/*/voltage_2': 'V_2',
    'ros_sw_ethercat_parser_data/sensors/*/velocity_1': 'v_1',
    'ros_sw_ethercat_parser_data/sensors/*/velocity_2': 'v_2',
    'ros_sw_ethercat_parser_data/sensors/*/velocity_pivot': 'v_pivot',
    'ros_sw_ethercat_parser_data/sensors/*/temperature_1': 'T_1',
    'ros_sw_ethercat_parser_data/sensors/*/temperature_2': 'T_2',
    'ros_sw_ethercat_parser_data/sensors/*/accel_x': 'a_x',
    'ros_sw_ethercat_parser_data/sensors/*/accel_y': 'a_y',
    'ros_sw_ethercat_parser_data/sensors/*/accel_z': 'a_z',
    'ros_sw_ethercat_parser_data/sensors/*/gyro_x': 'theta_x',
    'ros_sw_ethercat_parser_data/sensors/*/gyro_y': 'theta_y',
    'ros_sw_ethercat_parser_data/sensors/*/gyro_z': 'theta_z',
    'ros_sw_ethercat_parser_data/sensors/*/pressure': 'P'
}

cmd_vel_var_name_mapping = {
    'ros_ropod_cmd_vel/linear/x': 'x',
    'ros_ropod_cmd_vel/linear/y': 'y',
    'ros_ropod_cmd_vel/angular/z': 'theta'
}

data_thread = None
data_thread_lock = threading.Lock()

def create_blueprint(communicator):
    real_time_monitoring = Blueprint('real_time_monitoring', __name__)
    zyre_communicator = communicator
    config = Config()
    robot_data_query_msgs = dict()
    robot_wheel_var_name_mapping = dict()

    @real_time_monitoring.route('/real_time_monitoring')
    def monitoring():
        session['uid'] = uuid.uuid4()
        return render_template('real_time_monitoring.html')

    @socketio.on('connect', namespace='/real_time_monitoring')
    def on_connect():
        robots = config.get_robots()
        emit('deployed_robots', json.dumps(robots))
        setup_robot_query_params(robots)

    @real_time_monitoring.route('/real_time_monitoring/monitor_robot')
    def monitor_robot():
        robot_id = request.args.get('robot_id', '', type=str)

        client_feedback_msg = ''
        try:
            global data_thread
            with data_thread_lock:
                if data_thread is None:
                    data_thread = socketio.start_background_task(target=get_robot_data,
                                                                 robot_id=robot_id)
        except Exception as exc:
            print('[monitor_robot] %s' % str(exc))
            client_feedback_msg = 'Data could not be retrieved'
        return jsonify(success=True, message=client_feedback_msg)

    def get_robot_data(robot_id):
        robot_smart_wheel_count = config.get_robot_smart_wheel_count(robot_id)

        while True:
            data_msg = zyre_communicator.get_query_data(robot_data_query_msgs[robot_id])
            variables, data = DataUtils.parse_bb_latest_data_msg(data_msg)

            short_vel_vars = [cmd_vel_var_name_mapping[x] for x in cmd_vel_vars]
            wheel_data = []
            for i in range(robot_smart_wheel_count):
                wheel_data.append({})
                for var in wheel_vars:
                    expanded_var_name = var.replace('*', str(i))
                    wheel_data[i][expanded_var_name] = None

            vel_data = list()
            if variables:
                try:
                    for i in range(robot_smart_wheel_count):
                        for var in wheel_vars:
                            expanded_var_name = var.replace('*', str(i))
                            wheel_data[i][expanded_var_name] = data[variables.index(expanded_var_name)]
                    socketio.emit('wheel_data',
                                  json.dumps({'variables': robot_wheel_var_name_mapping[robot_id],
                                              'data': wheel_data}),
                                  namespace='/real_time_monitoring')
                except ValueError as exc:
                    print('[real_time_monitoring] Smart wheel data error')
                    print(str(exc))

                try:
                    vel_data = [data[variables.index(x)] for x in cmd_vel_vars]
                    socketio.emit('cmd_vel_data',
                                  json.dumps({'variables': short_vel_vars,
                                              'data': vel_data}),
                                  namespace='/real_time_monitoring')
                except ValueError as exc:
                    print('[real_time_monitoring] Velocity data error')
                    print(str(exc))

            socketio.sleep(1)

    def setup_robot_query_params(robots):
        for robot in robots:
            # for each robot, we expand the smart wheel variable names
            # depending on the robot's smart wheel count, combine the
            # query variables into a single list, and generate a robot-specific
            # data query message
            black_box_id = BBUtils.get_bb_id(robot)
            robot_smart_wheel_count = config.get_robot_smart_wheel_count(robot)
            expanded_wheel_vars = DataUtils.expand_var_names(wheel_vars, robot_smart_wheel_count)
            query_vars = expanded_wheel_vars + cmd_vel_vars
            query_msg = DataUtils.get_bb_latest_data_query_msg(session['uid'].hex,
                                                               black_box_id,
                                                               query_vars)
            robot_data_query_msgs[robot] = query_msg

            # for each robot, we get a short variable name mapping for the smart wheel variables
            robot_wheel_var_name_mapping[robot] = []
            for i in range(robot_smart_wheel_count):
                robot_wheel_var_name_mapping[robot].append({})
                for var in wheel_var_name_mapping:
                    var_name = var.replace('*', str(i+1))
                    robot_wheel_var_name_mapping[robot][i][var_name] = wheel_var_name_mapping[var]

    return real_time_monitoring
