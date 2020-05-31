from __future__ import print_function
import pymongo as pm
from flask_socketio import SocketIO
import math

socketio = SocketIO()

class Config(object):
    ROBOT_COLLECTION = 'robots'
    EXPERIMENT_COLLECTION = 'experiments'
    MAP_COLLECTION = 'maps'
    QUERY_COLLECTION = 'queries'

    def __init__(self):
        self.db_name = 'remote_monitoring_config'
        self.db_port = 27017

    def get_robots(self):
        '''Returns a list of all known robot names.
        '''
        collection_name = Config.ROBOT_COLLECTION
        client = pm.MongoClient(port=self.db_port)
        db = client[self.db_name]
        collection = db[collection_name]
        docs = collection.find({})
        robots = [doc['name'] for doc in docs]
        return robots

    def get_robot_smart_wheel_count(self, robot_id):
        '''Returns the number of smart wheels of the given robot.

        Keyword arguments:
        robot_id -- ID of a robot

        '''
        collection_name = Config.ROBOT_COLLECTION
        client = pm.MongoClient(port=self.db_port)
        db = client[self.db_name]
        collection = db[collection_name]
        doc = collection.find_one({'name': robot_id})
        if doc:
            return doc['smart_wheel_count']
        print('{0} does not exist'.format(robot_id))
        return 0

    def get_experiments(self):
        '''Returns a list of dictionaries of the form
        {
            "id": experiment_id,
            "name": descriptive_experiment_name
        }
        '''
        collection_name = Config.EXPERIMENT_COLLECTION
        client = pm.MongoClient(port=self.db_port)
        db = client[self.db_name]
        collection = db[collection_name]
        docs = collection.find({})
        experiments = [{'id': doc['id'], 'name': doc['name']} for doc in docs]
        return experiments

    def get_current_map(self):
        collection_name = Config.MAP_COLLECTION
        client = pm.MongoClient(port=self.db_port)
        db = client[self.db_name]
        collection = db[collection_name]
        docs = collection.find({'current_map': {"$exists":"true"}})
        return docs[0]['current_map']

    def get_map(self, map_name):
        collection_name = Config.MAP_COLLECTION
        client = pm.MongoClient(port=self.db_port)
        db = client[self.db_name]
        collection = db[collection_name]
        docs = collection.find({'name': map_name})
        return docs[0]

    def get_maps(self):
        collection_name = Config.MAP_COLLECTION
        client = pm.MongoClient(port=self.db_port)
        db = client[self.db_name]
        collection = db[collection_name]
        docs = collection.find({})
        maps = [doc for doc in docs if 'name' in doc.keys()]
        return maps

    def get_queries(self) :
        '''Returns a list of all known queries

        :Returns: list of dict

        '''
        collection_name = Config.QUERY_COLLECTION
        client = pm.MongoClient(port=self.db_port)
        db = client[self.db_name]
        collection = db[collection_name]
        docs = collection.find({})
        queries = [{'id': doc['id'], 'name': doc['name']} for doc in docs]
        return queries

class MapUtils(object):

    def __init__(self):
        pass

    def get_robot_pose_msg(self, msg):
        robot_pose_msg = dict()
        robot_pose_msg['robotId'] = msg['payload']['robotId']
        robot_pose_msg['x'] = msg['payload']['pose']['x']
        robot_pose_msg['y'] = msg['payload']['pose']['y']
        robot_pose_msg['theta'] = msg['payload']['pose']['theta']
        t1 = float(msg['payload']['pose']['theta']) + (9*math.pi/10.0)
        t2 = float(msg['payload']['pose']['theta']) - (9*math.pi/10.0)
        robot_pose_msg['line1x'] = (msg['payload']['pose']['x'] + 2*math.cos(t1))
        robot_pose_msg['line1y'] = (msg['payload']['pose']['y'] + 2*math.sin(t1))
        robot_pose_msg['line2x'] = (msg['payload']['pose']['x'] + 2*math.cos(t2))
        robot_pose_msg['line2y'] = (msg['payload']['pose']['y'] + 2*math.sin(t2))
        robot_pose_msg['timestamp'] = msg['header']['timestamp']
        return robot_pose_msg

msg_data = {
    "header":
    {
        "type": "",
        "version": "0.1.0",
        "metamodel": "ropod-msg-schema.json",
        "timestamp": ""
    },
    "payload":
    {
        "metamodel": "ropod-demo-cmd-schema.json",
        "senderId": ""
    }
}

robot_status_msg = {
    "header":
    {
        "type": "HEALTH-STATUS",
        "version": "0.1.0",
        "metamodel": "ropod-msg-schema.json",
        "msgId": None,
        "timestamp": None
    },
    "payload":
    {
        "metamodel": "ropod-component-monitor-schema.json",
        "robotId": None,
        "monitors": None
    }
}
