from __future__ import print_function
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request, session 

from common import Config

def create_blueprint(communicator):
    central_operator_console = Blueprint('central_operator_console', __name__)
    zyre_communicator = communicator
    config = Config()

    @central_operator_console.route('/central_operator_console')
    def index():
        session['uid'] = uuid.uuid4()
        return render_template('central_operator_console.html')

    @central_operator_console.route(
            '/central_operator_console/get_query_list', methods=['GET'])
    def get_query_list():
        feedback_msg = ''
        try:
            queries = config.get_queries()
            print(queries)
        except Exception as exc:
            print('[get_experiment_list] %s' % str(exc))
            feedback_msg = 'An error occurred while retrieving the experiment list'
        return jsonify(queries=queries, message=feedback_msg)

    @central_operator_console.route(
            '/central_operator_console/send_query_request', methods=['GET', 'POST'])
    def send_query_request():
        '''send query request to fms query interface via ZyreWebCommunicator 
        through pyre message
        '''
        query_type = request.args.get('query_id', '', type=str)
        query_type = query_type.upper().replace("_", "-")
        print(query_type)
        
        robot_id = request.args.get('robot_id', '', type=str)
        task_id = request.args.get('task_id', '', type=str)

        query_msg = {'header':{}, 'payload': {}}
        query_msg['header']['type'] = query_type
        query_msg['header']['timestamp'] = datetime.now().timestamp()
        query_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        query_msg['header']['msgId'] =  uuid.uuid4()

        query_msg['payload']['senderId'] = str(session['uid'])
        query_msg['payload']['robotId'] = robot_id
        query_msg['payload']['taskId'] = task_id
        print(query_msg)

        # query_msg = json.dumps(query_msg, indent=2, default=str)
        query_result = zyre_communicator.get_query_data(query_msg)
        if query_result is None :
            return jsonify(response=" ", message="Received no response from query interface")
        print("received results")

        return jsonify(response=query_result['payload'], message="")

    return central_operator_console
