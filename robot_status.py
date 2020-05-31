from __future__ import print_function
import json
import uuid
import threading

from flask import Blueprint, render_template, session
from flask_socketio import emit

from common import socketio, Config

status_thread = None
status_thread_lock = threading.Lock()

def create_blueprint(communicator):
    robot_status = Blueprint('robot_status', __name__)
    zyre_communicator = communicator
    config = Config()

    @robot_status.route('/')
    @robot_status.route('/robot_status')
    def robot_info():
        session['uid'] = uuid.uuid4()
        return render_template('robot_status.html')

    @socketio.on('connect', namespace='/robot_status')
    def on_connect():
        robots = config.get_robots()
        emit('deployed_robots', json.dumps(robots))

        global status_thread
        with status_thread_lock:
            if status_thread is None:
                status_thread = socketio.start_background_task(target=get_robot_status,
                                                               robot_ids=robots)

    def get_robot_status(robot_ids):
        while True:
            for robot in robot_ids:
                status_msg = zyre_communicator.get_status(robot)
                socketio.emit('status_msg', status_msg, namespace='/robot_status')
            socketio.sleep(0.1)

    return robot_status
