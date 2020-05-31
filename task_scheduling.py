from __future__ import print_function
import uuid
import threading

from flask import Blueprint, jsonify, render_template, request, session
from flask_socketio import emit

from common import msg_data, Config, socketio, MapUtils

status_thread = None
status_thread_lock = threading.Lock()

def create_blueprint(communicator):
    task_scheduling = Blueprint('task_scheduling', __name__)
    zyre_communicator = communicator
    config = Config()
    map_utils = MapUtils()

    @task_scheduling.route('/schedule_task')
    def run_experiment():
        session['uid'] = uuid.uuid4()
        return render_template('schedule_task.html')

    @task_scheduling.route('/task/get_locations')
    def get_locations():
        locations = [{'name': 'ALP-AKH, Standard-Abladepunkt', 'id': 'pickup_location'},
                     {'name': 'AKH934500, Ward 45, Room 14', 'id': 'delivery_location'}]
        return jsonify(locations=locations, message='')

    @task_scheduling.route('/task/get_device_types')
    def get_device_types():
        device_types = [{'name': 'Mobidik cart', 'id': 'mobidik'}]
        return jsonify(device_types=device_types, message='')

    @task_scheduling.route('/task/get_maps')
    def get_maps():
        maps = config.get_maps()
        for map_dict in maps:
            del map_dict['_id']
        return jsonify(maps=maps, message='')

    @task_scheduling.route('/task/send_task_request', methods=['POST'])
    def send_task_request():
        data = request.get_json()
        user_id = data.get('user_id')
        pickup_location = data.get('pickup_location')
        delivery_location = data.get('delivery_location')
        pickup_location_level = int(data.get('pickup_location_level'))
        delivery_location_level = int(data.get('delivery_location_level'))
        device_type = data.get('device_type')

        request_msg = dict(msg_data)
        request_msg['header']['type'] = "TASK-REQUEST"
        request_msg['payload']['userId'] = user_id
        request_msg['payload']['pickupLocation'] = pickup_location
        request_msg['payload']['deliveryLocation'] = delivery_location
        request_msg['payload']['pickupLocationLevel'] = pickup_location_level
        request_msg['payload']['deliveryLocationLevel'] = delivery_location_level
        request_msg['payload']['deviceType'] = device_type

        # where do we get the ID from?
        request_msg['payload']['deviceId'] = '1234567890'
        zyre_communicator.shout(request_msg)
        return jsonify(message='')

    @socketio.on('connect', namespace='/task_scheduling')
    def on_connect():
        current_map = config.get_current_map()
        map_msg = config.get_map(current_map)
        map_msg.pop('_id', None)
        socketio.emit('map', map_msg, namespace='/task_scheduling')

        robots = config.get_robots()
        global status_thread
        with status_thread_lock:
            if status_thread is None:
                status_thread = socketio.start_background_task(target=emit_robot_pose,
                                                               robot_ids=robots)

    def emit_robot_pose(robot_ids):
        while True:
            robot_pose_msg_list = list()
            for robot in robot_ids:
                msg = zyre_communicator.get_pose(robot)
                if msg:
                    robot_pose_msg_list.append(map_utils.get_robot_pose_msg(msg))
            if robot_pose_msg_list:
                socketio.emit('robot_pose', robot_pose_msg_list, namespace='/task_scheduling')
            socketio.sleep(1.0)

    return task_scheduling

