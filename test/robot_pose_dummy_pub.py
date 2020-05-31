#! /usr/bin/env python3
'''
This module publishes dummy pose 2d messages like below to test remote monotoring's
map selection feature
'''
from __future__ import print_function
'''
MESSAGE EXAMPLE
{
  "header":{
    "type":"ROBOT-POSE-2D",
    "metamodel":"ropod-msg-schema.json",
    "msgId":"5073dcfb-4849-42cd-a17a-ef33fa7c7a69"
  },
  "payload":{
    "metamodel":"ropod-demo-robot-pose-2d-schema.json",
    "robotId":"ropod_0",
    "pose":{
      "referenceId":"basement_map",
      "x":10,
      "y":20,
      "theta":3.1415
    }
  }
}
'''

import time
import json

from ropod.pyre_communicator.base_class import RopodPyre
from ropod.utils.models import MessageFactory
from ropod.utils.uuid import generate_uuid

class DummyPosePublisher(RopodPyre):

    """This class publishes dummy pose of robot/s with a given frequency"""

    def __init__(self):
        super(DummyPosePublisher, self).__init__({
            'node_name': 'dummy_pose_publisher',
            'groups': ['ROPOD'],
            'message_types': []},
            verbose=False,
            acknowledge=False)
        self.start()

    def send_message(self, msg_type, payload_dict=None):
        query_msg = MessageFactory.get_header(msg_type, recipients=[])

        query_msg['payload'] = {}
        query_msg['payload']['senderId'] = generate_uuid()
        if payload_dict is not None :
            for key in payload_dict.keys() :
                query_msg['payload'][key] = payload_dict[key]

        print(json.dumps(query_msg, indent=2, default=str))
        self.shout(query_msg)


if __name__ == "__main__":
    DUMMY_POSE_PUBLISHER = DummyPosePublisher()
    dummy_pose = {
      "referenceId":"basement_map",
      "x":0,
      "y":0,
      "theta":0.0
    }
    try:
        while True:
            DUMMY_POSE_PUBLISHER.send_message(
                'ROBOT-POSE-2D', 
                {
                    'metamodel':'ropod-demo-robot-pose-2d-schema.json',
                    'robotId':'ropod_001',
                    'pose':dummy_pose
                })
            time.sleep(1.0)
    except KeyboardInterrupt as e:
        print('Encountered following error\n', str(e))
    DUMMY_POSE_PUBLISHER.shutdown()
        
