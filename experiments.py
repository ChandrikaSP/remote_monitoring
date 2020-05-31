from __future__ import print_function
import uuid
import time
import threading
import json

from flask import Blueprint, jsonify, render_template, request, session

from data_utils import DataUtils

from common import socketio, msg_data, Config
from black_box_utils import BBUtils

feedback_thread = None
feedback_thread_lock = threading.Lock()

data_thread = None
data_thread_lock = threading.Lock()

experiment_diagnostic_vars = ['ros_sw_ethercat_parser_data/sensors/*/velocity_1',
                              'ros_sw_ethercat_parser_data/sensors/*/velocity_2',
                              'ros_sw_ethercat_parser_data/sensors/*/velocity_pivot',
                              'ros_sw_ethercat_parser_data/sensors/*/accel_x',
                              'ros_sw_ethercat_parser_data/sensors/*/accel_y',
                              'ros_sw_ethercat_parser_data/sensors/*/accel_z',
                              'ros_sw_ethercat_parser_data/sensors/*/gyro_x',
                              'ros_sw_ethercat_parser_data/sensors/*/gyro_y',
                              'ros_sw_ethercat_parser_data/sensors/*/gyro_z']

def create_blueprint(communicator):
    experiments = Blueprint('experiments', __name__)
    zyre_communicator = communicator
    config = Config()

    @experiments.route('/experiments')
    def run_experiment():
        session['uid'] = uuid.uuid4()
        return render_template('remote_experiments.html')

    @experiments.route('/experiments/get_robot_ids', methods=['GET'])
    def get_robot_ids():
        robots = list()
        feedback_msg = ''
        try:
            robots = config.get_robots()
        except Exception as exc:
            print('[get_robot_ids] %s' % str(exc))
            feedback_msg = 'An error occurred while retrieving the robot IDs'
        return jsonify(robots=robots, message=feedback_msg)

    @experiments.route('/experiments/get_sm', methods=['GET'])
    def get_sm():
        robot_id = request.args.get('robot_id', '', type=str)
        transitions = None
        feedback_msg = ''
        try:
            start_time = time.time()
            wait_threshold = 10.0
            while not transitions and time.time() < start_time + wait_threshold:
                transitions = zyre_communicator.get_experiment_sm(robot_id)
        except Exception as exc:
            print('[get_sm] %s' % str(exc))
            feedback_msg = 'An error occurred while retrieving the experiment SM transitions'
        return jsonify(transitions=transitions, message=feedback_msg)

    @experiments.route('/experiments/get_experiment_list', methods=['GET'])
    def get_experiment_list():
        experiments = dict()
        feedback_msg = ''
        try:
            experiments = config.get_experiments()
        except Exception as exc:
            print('[get_experiment_list] %s' % str(exc))
            feedback_msg = 'An error occurred while retrieving the experiment list'
        return jsonify(experiments=experiments, message=feedback_msg)

    @experiments.route('/experiments/send_experiment_request', methods=['GET', 'POST'])
    def send_experiment_request():
        '''Sends a "ROBOT-EXPERIMENT-REQUEST" message to a robot with ID "robot_id"
        for performing the experiment with ID "experiment" (both the robot ID and
        the experiment ID are expected to be passed in the request).
        '''
        robot_id = request.args.get('robot_id', '', type=str)
        experiment = request.args.get('experiment', '', type=str)

        msg = dict(msg_data)
        msg['header']['type'] = 'ROBOT-EXPERIMENT-REQUEST'
        msg['header']['robotId'] = robot_id
        msg['payload']['userId'] = session['uid'].hex
        msg['payload']['experimentType'] = experiment

        client_feedback_msg = ''
        try:
            zyre_communicator.shout(msg)

            global feedback_thread
            with feedback_thread_lock:
                if not feedback_thread:
                    feedback_thread = socketio.start_background_task(target=get_experiment_feedback,
                                                                     session_id=session['uid'].hex,
                                                                     robot_id=robot_id)
        except Exception as exc:
            print('[send_experiment_request] %s' % str(exc))
            client_feedback_msg = 'Command could not be sent'
        return jsonify(success=True, message=client_feedback_msg)

    @experiments.route('/experiments/remote_command', methods=['GET', 'POST'])
    def send_remote_command():
        robot_id = request.args.get('robot_id', '', type=str)
        command = request.args.get('command', '', type=str)

        msg = dict(msg_data)
        msg['header']['type'] = 'ROBOT-COMMAND'
        msg['header']['robotId'] = robot_id
        msg['payload']['userId'] = session['uid'].hex
        msg['payload']['command'] = command

        client_feedback_msg = ''
        try:
            zyre_communicator.shout(msg, groups=['ROPOD'])
        except Exception as exc:
            print('[remote_command] %s' % str(exc))
            client_feedback_msg = 'Command could not be sent'
        return jsonify(success=True)

    def get_experiment_feedback(session_id, robot_id):
        global data_thread
        experiment_ongoing = True
        feedback_received = False
        black_box_id = BBUtils.get_bb_id(robot_id)
        robot_smart_wheel_count = config.get_robot_smart_wheel_count(robot_id)
        diagnostic_vars = DataUtils.expand_var_names(experiment_diagnostic_vars,
                                                     robot_smart_wheel_count)

        zyre_communicator.reset_experiment_feedback(robot_id)
        while experiment_ongoing:
            feedback_msg = zyre_communicator.get_experiment_feedback(robot_id)
            if feedback_msg and feedback_msg['robot_id'] == robot_id:
                feedback_received = True
            experiment_ongoing = send_experiment_feedback(robot_id,
                                                          feedback_msg,
                                                          feedback_received)

            if experiment_ongoing:
                with data_thread_lock:
                    if not data_thread:
                        data_thread = threading.Thread(target=send_diagnostic_data,
                                                       kwargs={'session_id': session_id,
                                                               'black_box_id': black_box_id,
                                                               'diagnostic_vars': diagnostic_vars})
                        data_thread.start()

        global feedback_thread
        feedback_thread = None

    def send_experiment_feedback(robot_id, feedback_msg, prev_feedback_received):
        experiment_ongoing = True
        if feedback_msg and feedback_msg['robot_id'] == robot_id:
            if feedback_msg['feedback_type'] == 'ROBOT-EXPERIMENT-FEEDBACK':
                experiment_ongoing = False
            socketio.sleep(0.1)
        elif not feedback_msg:
            feedback_msg = dict()
            feedback_msg['timestamp'] = time.time()
            if prev_feedback_received:
                feedback_msg['feedback_type'] = 'ROBOT-EXPERIMENT-FEEDBACK'
                feedback_msg['result'] = '{0} is not responding anymore'.format(robot_id)
            else:
                feedback_msg['feedback_type'] = 'EXPERIMENT-ERROR'
                feedback_msg['result'] = '{0} is not responding; could not start experiment'.format(robot_id)
            experiment_ongoing = False

        socketio.emit('experiment_feedback',
                      json.dumps(feedback_msg),
                      namespace='/experiments')
        return experiment_ongoing

    def send_diagnostic_data(session_id, black_box_id, diagnostic_vars):
        end_query_time = int(time.time())
        start_query_time = end_query_time - 10

        query_msg = DataUtils.get_bb_query_msg(session_id,
                                               black_box_id,
                                               diagnostic_vars,
                                               start_query_time,
                                               end_query_time)
        query_result = zyre_communicator.get_query_data(query_msg)

        try:
            variables, data = DataUtils.parse_bb_data_msg(query_result)
            vel_vars, vel_data = get_variable_data('velocity', variables, data)
            socketio.emit('vel_data',
                          json.dumps({'variables': vel_vars,
                                      'data': vel_data}),
                          namespace='/experiments')

            accel_vars, accel_data = get_variable_data('accel', variables, data)
            socketio.emit('accel_data',
                          json.dumps({'variables': accel_vars,
                                      'data': accel_data}),
                          namespace='/experiments')

            gyro_vars, gyro_data = get_variable_data('gyro', variables, data)
            socketio.emit('gyro_data',
                          json.dumps({'variables': gyro_vars,
                                      'data': gyro_data}),
                          namespace='/experiments')
        except Exception as exc:
            print('[send_diagnostic_data] {0} does not seem to be responding'.format(black_box_id))
            print(str(exc))

        global data_thread
        data_thread = None

    def get_variable_data(var_name_component, variables, data):
        filtered_variables = list()
        filtered_data = list()
        if data:
            for i, var in enumerate(variables):
                if var.find(var_name_component) != -1:
                    filtered_variables.append(var)
                    filtered_data.append(data[i])
        return filtered_variables, filtered_data

    return experiments
