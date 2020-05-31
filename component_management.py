import json
import uuid
import threading

from flask import Blueprint, render_template, session, request, jsonify
from flask_socketio import emit

from common import socketio, Config, msg_data

status_thread = None
status_thread_lock = threading.Lock()

def create_blueprint(communicator):
    component_management = Blueprint('component_management', __name__)
    zyre_communicator = communicator
    config = Config()

    @component_management.route('/component_management')
    def robot_info():
        session['uid'] = uuid.uuid4()
        return render_template('component_management.html')

    @component_management.route('/component_management/manage_components', methods=['POST'])
    def manage_components():
        request_data = request.get_json()
        robot_id = request_data.get('robot_id', '')
        action = request_data.get('action', '')
        components = request_data.get('components', [])
        if not components:
            return jsonify(error=True, message='No components selected')

        msg = dict(msg_data)
        msg['header']['type'] = 'COMPONENT-MANAGEMENT-REQUEST'
        msg['header']['robotId'] = robot_id
        msg['header']['userId'] = session['uid'].hex
        msg['payload']['metamodel'] = 'ropod-component-management-request.json'
        msg['payload']['components'] = components
        msg['payload']['action'] = action
        result_msg = zyre_communicator.get_query_data(msg)

        client_feedback_msg = ''
        error = False
        try:
            managed_components = result_msg['payload']['components']
            if managed_components:
                client_feedback_msg = 'The {0} operation was successful for the following components: '.format(action)
                client_feedback_msg += ', '.join(managed_components[:-1]) + ', ' + managed_components[-1]
            else:
                client_feedback_msg = 'The {0} operation was unsuccessful'.format(action)
                error = True
        except Exception as exc:
            print('[manage_components] %s' % str(exc))
            client_feedback_msg = 'Command could not be sent'
            error = True
        return jsonify(message=client_feedback_msg, error=error)

    @socketio.on('connect', namespace='/component_management')
    def on_connect():
        robots = config.get_robots()
        emit('deployed_robots', json.dumps(robots))

        global status_thread
        with status_thread_lock:
            if status_thread is None:
                status_thread = socketio.start_background_task(target=get_robot_status,
                                                               robot_ids=robots)

    def get_robot_status(robot_ids):
        robot_status_msgs = {robot: {'robot_id': robot,
                                     'timestamp': None,
                                     'component_statuses': dict()} for robot in robot_ids}
        while True:
            for robot in robot_ids:
                status_msg = zyre_communicator.get_status(robot)
                if status_msg['payload']['monitors'] is not None:
                    component_statuses = get_component_statuses(status_msg)
                    robot_status_msgs[robot]['timestamp'] = status_msg['header']['timestamp']
                    robot_status_msgs[robot]['component_statuses'] = component_statuses
                else:
                    robot_status_msgs[robot]['component_statuses'] = None
                socketio.emit('status_msg', robot_status_msgs[robot], namespace='/component_management')
            socketio.sleep(0.1)

    def get_component_statuses(status_msg):
        component_statuses = dict()
        for component_data in status_msg['payload']['monitors']:
            if component_data['component_id'] == 'systemd':
                component_statuses = component_data['modes'][0]['healthStatus']

        # we remove the global status field from the component status message
        if 'status' in component_statuses:
            del component_statuses['status']
        return component_statuses

    return component_management
