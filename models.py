from timestamp import TimeStamp
from uuid import generate_uuid
from task import Task, TaskRequest
from elevator import ElevatorRequest, RobotCallUpdate, RobotElevatorCallReply

meta_model_template = 'ropod-%s-schema.json'


class MessageFactoryBase(object):
    def __init__(self):
        self.factories = {}
        self.messages = {}

    def register_factory(self, factory_name, factory):
        self.factories[factory_name] = factory

    def register_msg(self, message_name, factory):
        self.messages[message_name] = factory

    def get_factory(self, message_name):
        for factory_name, factory in self.factories.items():
            if message_name in factory.messages:
                return factory

    def create_message(self, contents, recipients=[]):
        pass

    @staticmethod
    def get_header(message_type, meta_model='msg', recipients=[]):
        if recipients is not None and not isinstance(recipients, list):
            raise Exception("Recipients must be a list of strings")

        return {"header": {'type': message_type,
                           'metamodel': 'ropod-%s-schema.json' % meta_model,
                           'msgId': generate_uuid(),
                           'timestamp': TimeStamp().to_str(),
                           'receiverIds': recipients}}

    @staticmethod
    def get_payload(contents, model):
        payload = contents.to_dict()
        metamodel = meta_model_template % model
        payload.update(metamodel=metamodel)
        return {"payload": payload}

    @staticmethod
    def update_timestamp(message):
        header = message.get('header')
        if header:
            header.update(timeStamp=TimeStamp().to_str())
        else:
            header = MessageFactoryBase.get_header(None)
            message.update(header)

    @staticmethod
    def update_msg_id(message, id=None):
        header = message.get('header')

        if header:
            if id:
                header.update(msgId=id)
            else:
                header.update(msgId=generate_uuid())
        else:
            header = MessageFactoryBase.get_header(None)
            message.update(header)

    @staticmethod
    def get_acknowledge_msg(message):
        msg = MessageFactoryBase.get_header('ACKNOWLEDGEMENT')
        message_id = message.get('header').get('msgId')
        payload = {'payload': {'receivedMsg': message_id}}
        msg.update(payload)
        return msg


class RopodMessageFactory(MessageFactoryBase):
    def __init__(self):
        super().__init__()

        self.register_msg(Task.__name__, self)
        self.register_msg(TaskRequest.__name__, self)
        self.register_msg(ElevatorRequest.__name__, self)
        self.register_msg(RobotCallUpdate.__name__, self)
        self.register_msg(RobotElevatorCallReply.__name__, self)

    def create_message(self, contents, recipients=[]):
        if isinstance(contents, Task):
            model = 'TASK'
        elif isinstance(contents, TaskRequest):
            model = 'TASK-REQUEST'
        elif isinstance(contents, ElevatorRequest):
            model = 'ELEVATOR-CMD'
        elif isinstance(contents, RobotCallUpdate):
            model = 'ROBOT-CALL-UPDATE'
        elif isinstance(contents, RobotElevatorCallReply):
            model = 'ROBOT-ELEVATOR-CALL-REPLY'

        msg = self.get_header(model, recipients=recipients)
        payload = self.get_payload(contents, model.lower())
        msg.update(payload)
        return msg

    def get_query_msg(self, msg_type, payload_key, payload_value, success, receiverId):
        '''Returns a dictionary representing a query response for the given
        message type.
        Assumption: header uses 'ropod-msg-schema.json' meta model

        Keyword arguments:
        :msg_type: a string representing a message type
        :payload_key: string representing key for payload
        :payload_value: list/dict representing the response of the query
        :success: boolean
        :receiverId: string

        '''
        response_msg = self.get_header(msg_type, recipients=[])
        response_msg['payload'] = dict()
        response_msg['payload'][payload_key] = payload_value
        response_msg['payload']['success'] = success
        response_msg['payload']['receiverId'] = receiverId
        return response_msg


