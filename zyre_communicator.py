from copy import deepcopy
import time
from ropod.pyre_communicator.base_class import RopodPyre
from remote_monitoring.common import Config, robot_status_msg

class ZyreWebCommunicator(RopodPyre):
    def __init__(self, node_name, groups, data_timeout=10., status_timeout=5.):
        '''
        Keyword arguments:
        node_name -- name of the zyre node
        groups -- groups that the node should join
        data_timeout -- timeout (in seconds) for data queries and messages (default 10.)
        status_timeout -- timeout (in seconds) for status queries and messages (default 5.)
        '''
        super(ZyreWebCommunicator, self).__init__({'node_name': node_name,
                                                   'groups': groups,
                                                   'message_types': []})

        # timeout (in seconds) for data queries and messages
        self.__data_timeout = data_timeout

        # timeout (in seconds) for status queries and messages
        self.__status_timeout = status_timeout

        # a dictionary in which the keys are session IDs
        # and the values are types of requests for the particular users
        self.__request_type = dict()

        # a dictionary in which the keys are session IDs
        # and the values are robots to which the requests are sent
        self.__request_robots = dict()

        # a dictionary in which the keys are session IDs
        # and the values are messages for the particular users
        self.__request_data = dict()

        # a dictionary in which the keys are robot IDs
        # and the values are robot status messages
        self.__status_msgs = dict()

        # a dictionary in which the keys are robot IDs
        # and the values are experiment feedback messages
        self.__experiment_feedback_msgs = dict()

        # a dictionary in which the keys are robot IDs
        # and the values are the corresponding robot poses
        self.__robot_pose_msgs = dict()

        # a dictionary in which the keys are robot IDs
        # and the values are the corresponding robot's experiment SM transitions
        self.__sm_msgs = dict()

        config = Config()
        robots = config.get_robots()
        for robot in robots:
            status_msg = deepcopy(robot_status_msg)
            status_msg['payload']['robotId'] = robot
            self.__status_msgs[robot] = status_msg
            self.__experiment_feedback_msgs[robot] = None
            self.__robot_pose_msgs[robot] = None
        self.start()

    def receive_msg_cb(self, msg_content):
        '''Processes incoming messages. Only listens to messages of type
        "VARIABLE_QUERY", "DATA_QUERY", "HEALTH-STATUS", "ROBOT-COMMAND-FEEDBACK",
        "ROBOT-EXPERIMENT-FEEDBACK", and "TASK-PROGRESS"; ignores all other message types

        Keyword arguments:
        msg_content -- a zyre message in string format

        '''
        dict_msg = self.convert_zyre_msg_to_dict(msg_content)
        if dict_msg is None:
            return

        timestamp = dict_msg['header']['timestamp']
        message_type = dict_msg['header']['type']
        if message_type == 'VARIABLE-QUERY' or message_type == 'DATA-QUERY' or \
           message_type == 'LATEST-DATA-QUERY':
            for session_id in self.__request_data:
                if dict_msg['payload']['receiverId'] == session_id:
                    self.__request_data[session_id] = dict_msg
        elif message_type == 'HEALTH-STATUS':
            robot_id = dict_msg['payload']['robotId']
            if robot_id in self.__status_msgs:
                self.__status_msgs[robot_id] = dict_msg
        elif message_type == 'ROBOT-COMMAND-FEEDBACK':
            robot_id = dict_msg['payload']['robotId']
            if robot_id in self.__experiment_feedback_msgs:
                feedback_data = dict()
                feedback_data['timestamp'] = timestamp
                feedback_data['feedback_type'] = message_type
                feedback_data['robot_id'] = dict_msg['payload']['robotId']
                feedback_data['command'] = dict_msg['payload']['command']
                feedback_data['state'] = dict_msg['payload']['state']
                self.__experiment_feedback_msgs[robot_id] = feedback_data
        elif message_type == 'ROBOT-EXPERIMENT-FEEDBACK':
            robot_id = dict_msg['payload']['robotId']
            if robot_id in self.__experiment_feedback_msgs:
                feedback_data = dict()
                feedback_data['timestamp'] = timestamp
                feedback_data['feedback_type'] = message_type
                feedback_data['robot_id'] = dict_msg['payload']['robotId']
                feedback_data['experiment'] = dict_msg['payload']['experimentType']
                feedback_data['result'] = dict_msg['payload']['result']
                self.__experiment_feedback_msgs[robot_id] = feedback_data
        elif message_type == 'TASK-PROGRESS':
            for session_id in self.__request_data:
                if self.__request_type[session_id] == 'TASK-PROGRESS' and \
                   self.__request_robots[session_id] == dict_msg['payload']['robotId']:
                    feedback_data = dict()
                    feedback_data['timestamp'] = timestamp
                    feedback_data['robot_id'] = dict_msg['payload']['robotId']
                    feedback_data['action_type'] = dict_msg['payload']['actionType']
                    feedback_data['action_status'] = dict_msg['payload']['status']['actionStatus']
                    feedback_data['task_status'] = dict_msg['payload']['status']['taskStatus']
                    if 'sequenceNumber' in dict_msg['payload']['status']:
                        feedback_data['sequence_number'] = dict_msg['payload']['status']['sequenceNumber']
                    if 'totalNumber' in dict_msg['payload']['status']:
                        feedback_data['total_number'] = dict_msg['payload']['status']['totalNumber']
                    self.__request_data[session_id] = feedback_data
        elif message_type == 'ROBOT-POSE-2D':
            robot_id = dict_msg['payload']['robotId']
            if robot_id in self.__robot_pose_msgs:
                self.__robot_pose_msgs[robot_id] = dict_msg
        elif message_type in ["GET-ALL-ONGOING-TASKS", "GET-ALL-SCHEDULED-TASKS",
                "GET-ALL-SCHEDULED-TASK-IDS", "GET-ROBOTS-ASSIGNED-TO-TASK",
                "GET-TASKS-ASSIGNED-TO-ROBOT"] :
            for session_id in self.__request_data:
                if dict_msg['payload']['receiverId'] == session_id:
                    self.__request_data[session_id] = dict_msg
        elif message_type == 'COMP-MON-CONFIG':
            receiver_id = dict_msg.get('payload', {'receiverId':None}).get('receiverId', None)
            if receiver_id in self.__request_data:
                self.__request_data[receiver_id] = dict_msg
        elif message_type == 'ROBOT-EXPERIMENT-SM':
            robot_id = dict_msg['payload']['robotId']
            self.__sm_msgs[robot_id] = dict_msg['payload']['transitions']
        elif message_type == 'COMPONENT-MANAGEMENT-RESPONSE':
            for session_id in self.__request_data:
                if dict_msg['payload']['receiverId'] == session_id:
                    self.__request_data[session_id] = dict_msg

    def get_query_data(self, query_msg):
        '''Queries data and waits for a response

        Keyword arguments:
        query_msg -- a dictionary query message

        '''
        session_id = query_msg['payload']['senderId']
        self.__request_data[session_id] = None
        self.shout(query_msg)
        data = self.__wait_for_data(session_id)
        return data

    #####################
    # Component monitors
    #####################
    def get_status(self, robot_id):
        '''Returns a dictionary representing the status of the given robot

        Keyword arguments:
        robot_id -- ID of a robot whose status needs to be retrieved

        '''
        if self.__status_msgs[robot_id] and self.__status_msgs[robot_id]['header']['timestamp']:
            time_since_last_msg = time.time() - self.__status_msgs[robot_id]['header']['timestamp']
            if time_since_last_msg > self.__status_timeout:
                self.__status_msgs[robot_id]['payload']['monitors'] = None
        return self.__status_msgs[robot_id]

    #####################
    # Robot pose
    #####################
    def get_pose(self, robot_id):
        if robot_id in self.__robot_pose_msgs.keys() and self.__robot_pose_msgs[robot_id]:
            return self.__robot_pose_msgs[robot_id]
        else:
            return None

    #####################
    # Remote experiments
    #####################
    def reset_experiment_feedback(self, robot_id):
        '''Resets the experiment feedback messages for the given robot.

        Keyword arguments:
        robot_id -- ID of a robot

        '''
        self.__experiment_feedback_msgs[robot_id] = None

    def get_experiment_feedback(self, robot_id):
        '''Returns a dictionary representing an experiment feedback message from the given robot

        Keyword arguments:
        robot_id -- ID of a robot whose feedback is asked for

        '''
        # if there are no experiment feedback messages, we wait until we
        # get one or until the status timeout is reached
        start_time = time.time()
        elapsed_time = 0.
        while not self.__experiment_feedback_msgs[robot_id] and elapsed_time < self.__status_timeout:
            time.sleep(0.1)
            elapsed_time = time.time() - start_time

        # if we do have a saved feedback message, but it was received
        # a long time ago, we clear the message
        if self.__experiment_feedback_msgs[robot_id]:
            last_msg_time_diff = time.time() - self.__experiment_feedback_msgs[robot_id]['timestamp']
            if last_msg_time_diff > self.__status_timeout:
                self.__experiment_feedback_msgs[robot_id] = None

        feedback_msg = self.__experiment_feedback_msgs[robot_id]
        if feedback_msg and feedback_msg['feedback_type'] == 'ROBOT-EXPERIMENT-FEEDBACK':
            self.__experiment_feedback_msgs[robot_id] = None
        return feedback_msg

    def get_experiment_sm(self, robot_id):
        if robot_id in self.__sm_msgs.keys() and self.__sm_msgs[robot_id]:
            sm = self.__sm_msgs[robot_id]
            del self.__sm_msgs[robot_id]
            return sm
        else:
            return None

    #################
    # Task execution
    #################
    def get_task_feedback(self, session_id, robot_id):
        '''Returns a dictionary representing the a task progress message

        Keyword arguments:
        session_id -- Session ID of a user requesting data

        '''
        self.__request_data[session_id] = None
        self.__request_robots[session_id] = robot_id
        self.__request_type[session_id] = 'TASK-PROGRESS'
        task_feedback = self.__wait_for_data(session_id)
        return task_feedback

    def __wait_for_data(self, session_id):
        '''Waits for incoming data for the user with the provided session ID
        and returns the received data. Returns None if not data is received
        within "self.__data_timeout" seconds

        Keyword arguments:
        session_id -- Session ID of a user requesting data

        '''
        start_time = time.time()
        elapsed_time = 0.
        while not self.__request_data[session_id] and elapsed_time < self.__data_timeout:
            time.sleep(0.1)
            elapsed_time = time.time() - start_time

        data = None
        if self.__request_data[session_id]:
            data = self.__request_data[session_id]

        self.__request_data.pop(session_id)
        if session_id in self.__request_robots:
            self.__request_robots.pop(session_id)
        if session_id in self.__request_type:
            self.__request_type.pop(session_id)
        return data
