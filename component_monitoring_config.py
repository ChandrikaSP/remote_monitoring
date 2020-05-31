from __future__ import print_function
import uuid
import json
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request, session 

from common import Config

def create_blueprint(communicator):
    central_operator_console = Blueprint('component_monitoring_config', __name__)
    zyre_communicator = communicator
    config = Config()

    @central_operator_console.route('/component_monitoring_config')
    def index():
        session['uid'] = uuid.uuid4()
        return render_template('component_monitoring_config.html')

    @central_operator_console.route(
            '/component_monitoring_config/get_config', methods=['GET'])
    def get_config():
        '''send query request to component_monitoring query interface via ZyreWebCommunicator 
        through pyre message. Send the received response to front end.
        '''
        robot_id = request.args.get('robot_id', '', type=str)
        query_msg = {'header':{}, 'payload': {}}
        query_msg['header']['type'] = 'COMP-MON-CONFIG'
        query_msg['header']['timestamp'] = datetime.now().timestamp()
        query_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        query_msg['header']['msgId'] =  uuid.uuid4()

        query_msg['payload']['senderId'] = str(session['uid'])
        query_msg['payload']['robotId'] = robot_id
        print(json.dumps(query_msg, indent=2, default=str))
        query_result = zyre_communicator.get_query_data(query_msg)
        if query_result is None :
            return jsonify(
                    response=" ", 
                    message="Received no response from component monitoring query interface")
        else:
            # print(json.dumps(query_result['payload'], indent=2, default=str))
            return jsonify(response=query_result['payload'], message="")

    return central_operator_console
