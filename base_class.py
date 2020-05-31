import time
import json
import zmq
import ast
import logging
from uuid import UUID
from datetime import timedelta, datetime
from timestamp import TimeStamp as ts
from uuid import generate_uuid

from base_class import PyreBase
from models import RopodMessageFactory

ZYRE_SLEEP_TIME = 0.250  # type: float


class RopodPyre(PyreBase):
    def __init__(self, zyre_config, **kwargs):
        """
        :param zyre_config: a dictionary containing the parameters for the pyre base class:
                            node_name: a string containing the name of the node
                            groups: a list of strings containing the groups the node will join
                            message_types: a list of strings containing the message types to acknowledge
                            interface: sets the interface to be used by the node
        :param acknowledge: boolean indicating whether the node should send acknowledgements for
                            shout and whispered messages
        :param ropod_uuid: a string containing the hexadecimal version of a nodes uuid
        :param extra_headers: a dictionary containing the additional headers
        """
        self.logger = logging.getLogger('RopodPyre')
        self.mf = RopodMessageFactory()

        self.acknowledge = kwargs.get('acknowledge', False)

        if self.acknowledge:
            self.unacknowledged_msgs = {}
            self.number_of_retries = kwargs.get('retries', 5)

        super(RopodPyre, self).__init__(**zyre_config)

        node_name = zyre_config.get('node_name')
        ropod_uuid = kwargs.get('ropod_uuid', None)
        extra_headers = kwargs.get('extra_headers', dict())

        self.set_header('name', node_name)
        if ropod_uuid:
            self.set_header('uuid', ropod_uuid)
        else:
            self.set_header('uuid', str(self.uuid()))

        if extra_headers:
            for key in extra_headers:
                self.set_header(key, extra_headers[key])

        self.logger.info('Initialized %s', self.name())
        self.logger.debug("Zyre config: %s", zyre_config)
        self.logger.debug("Extra headers: %s ", extra_headers)
        self.logger.debug("Acknowledgements: %s", self.acknowledge)

    def receive_msg_cb(self, msg_content):
        pass

    def convert_zyre_msg_to_dict(self, msg):
        try:
            return ast.literal_eval(msg)
        except ValueError:
            try:
                return json.loads(msg)
            except Exception as e:
                self.logger.warning("Couldn't convert zyre_msg to dictionary")
                self.logger.warning(e)
                return None

    def receive_loop(self, ctx, pipe):

        poller = zmq.Poller()
        poller.register(pipe, zmq.POLLIN)
        poller.register(self.socket(), zmq.POLLIN)

        while not self.terminated:
            try:
                # Call the poller with a timeout of 1000 ms.
                # If a timeout occurs, items is empty, so we just check if we need to resend any messages.
                # This makes sure we check resending of messages at least every second.
                # Otherwise we're dependent on receiving a message to get out of the polling call.
                # If items is not empty, it means we've received a message on one of the pipes,
                #  so we parse the message etc.
                items = dict(poller.poll(1000))
                if not items and self.acknowledge:
                    self.resend_message_cb()
                elif pipe in items and items[pipe] == zmq.POLLIN:
                    message = pipe.recv()
                    if message.decode('utf-8') == "$$STOP":
                        break
                    print("CHAT_TASK: %s" % message)
                else:
                    self.received_msg = self.recv()

                    zyre_msg = self.get_zyre_msg()

                    if zyre_msg.msg_type in ('LEAVE', 'EXIT'):
                        continue
                    elif zyre_msg.msg_type == "STOP":
                        break
                    elif zyre_msg.msg_type not in ('SHOUT', 'WHISPER', 'JOIN', 'PING', 'PING_OK', 'HELLO', 'ENTER'):
                        self.logger.warning("Unrecognized message type: %s", zyre_msg.msg_type)

                    if self.acknowledge:
                        self.acknowledge_cb(zyre_msg)

                    self.zyre_event_cb(zyre_msg)

            except (KeyboardInterrupt, SystemExit):
                self.terminated = True
                break
        self.logger.info("Node %s exiting..." % self.name())

    def zyre_event_cb(self, zyre_msg):
        if zyre_msg.msg_type in ("SHOUT", "WHISPER"):
            self.receive_msg_cb(zyre_msg.msg_content)

    def acknowledge_cb(self, zyre_msg):
        if zyre_msg.msg_type in ('SHOUT', 'WHISPER'):
            self.send_acknowledgment(zyre_msg)
            self.check_unacknowledged_msgs(zyre_msg)

    def shout(self, msg, groups=None):
        """
        Shouts a message to a given group.
        For Python 3 encodes the string to utf-8

        Params:
            msg: the string to be sent
            groups: can be a string with the name of the group, or a list of
                    strings
        """

        if isinstance(msg, dict):
            if self.acknowledge:
                self.check_msg_retries(msg, "SHOUT", groups=groups)
            message = json.dumps(msg, default=str).encode('utf-8')
        else:
            message = msg.encode('utf-8')

        if groups:
            if isinstance(groups, list):
                for group in groups:
                    super(PyreBase, self).shout(group, message)
                    time.sleep(ZYRE_SLEEP_TIME)
            else:
                # TODO Do we need formatted strings?
                super(PyreBase, self).shout(groups, message)
        else:
            for group in self.groups():
                super(PyreBase, self).shout(group, message)

    def whisper(self, msg, peer):
        """
        Whispers a message to a peer.
        For Python 3 encodes the message to utf-8.

        Params:
            :string msg: the string to be sent
            :UUID peer: a single peer UUID
            :list peer: a list of peer UUIDs
            :string peer: the name of a peer
            :list peer: a list of peer names
        """

        if isinstance(msg, dict):
            # Add message to list of messages that need acknowledgment
            if self.acknowledge:
                self.check_msg_retries(msg, "WHISPER", peer=peer)

            message = json.dumps(msg, default=str).encode('utf-8')
        else:
            message = msg.encode('utf-8')

        if isinstance(peer, UUID):
            self.whisper_to_uuid(peer, message)
        elif isinstance(peer, list):
            for p in peer:
                time.sleep(ZYRE_SLEEP_TIME)
                if isinstance(p, UUID):
                    self.whisper_to_uuid(p, message)
                else:
                    self.whisper_to_name(p, message)
        elif isinstance(peer, str):
            self.whisper_to_name(peer, message)

    def whisper_to_uuid(self, peer, message):
        super(PyreBase, self).whisper(peer, message)

    def whisper_to_name(self, peer_name, message):
        for k, v in self.peer_directory.items():
            if v == peer_name:
                self.whisper_to_uuid(k, message)
                return

    def send_acknowledgment(self, zyre_msg):
        """
        This is a ROPOD-specific function to send acknowledgements to shouted and whispered messages defined in the
        node's constructor.
        Note that this assumes that the messages being received are writen in json, according to ropod-models.

        :param zyre_msg: zyre_msg which contains the message type, peer, group, and contents
        """

        if self.needs_acknowledgment(zyre_msg):
            contents = self.convert_zyre_msg_to_dict(zyre_msg.msg_content)
            ack_msg = self.mf.get_acknowledge_msg(contents)

            self.whisper(ack_msg, zyre_msg.peer_uuid)
        else:
            return

    def needs_acknowledgment(self, zyre_msg):
        if zyre_msg.msg_type not in ('SHOUT', 'WHISPER'):
            return False
        elif zyre_msg.msg_type == 'SHOUT' and zyre_msg.group_name not in self.own_groups():
            return False

        if zyre_msg.msg_content:
            contents = self.convert_zyre_msg_to_dict(zyre_msg.msg_content)
            header = contents.get('header')

            # if receiverIds are specified and this node is not listed there, don't send an acknowledgement
            if header.get('receiverIds', []) and self.name not in header.get('receiverIds', []):
                return False

            if header.get('type') in self.message_types:
                return True
        else:
            return False

    def check_msg_retries(self, message, zyre_msg_type, **kwargs):
        msg_type = message['header']['type']
        if msg_type not in self.message_types:
            return
        msg_id = message['header']['msgId']
        queued_msg = self.unacknowledged_msgs.get(msg_id, None)
        if queued_msg:
            retry = queued_msg.get('retry_number', 0)
            self.unacknowledged_msgs[msg_id]['retry_number'] = retry + 1
            self.unacknowledged_msgs[msg_id]['last_retry'] = self.unacknowledged_msgs[msg_id]['next_retry']

        else:
            self.unacknowledged_msgs[msg_id] = dict()
            self.unacknowledged_msgs[msg_id]['retry_number'] = 0
            current_ts = ts.get_time_stamp()
            self.unacknowledged_msgs[msg_id]['first_attempt'] = current_ts
            self.unacknowledged_msgs[msg_id]['last_retry'] = current_ts
            self.unacknowledged_msgs[msg_id]['zyre_msg_type'] = zyre_msg_type
            if 'receiverIds' in message['header'].keys():
                self.unacknowledged_msgs[msg_id]['receiverIds'] = message['header']['receiverIds']
            else:
                self.unacknowledged_msgs[msg_id]['receiverIds'] = list()
            self.unacknowledged_msgs[msg_id]['msg_args'] = dict()
            self.unacknowledged_msgs[msg_id]['msg_args']['msg'] = message
            self.unacknowledged_msgs[msg_id]['msg_args'].update(kwargs)
            deadline = timedelta(seconds=5 ** 5)
            self.unacknowledged_msgs[msg_id]['reply_by'] = ts.get_time_stamp(deadline)

        # TODO This needs to be probably adapted by message type
        next_attempt = timedelta(seconds=5)
        self.unacknowledged_msgs[msg_id]['next_retry'] = ts.get_time_stamp(next_attempt)

    def add_next_retry(self, msg_id):
        retry = self.unacknowledged_msgs[msg_id]['retry_number']
        timeout = 5 ** retry
        next_attempt = timedelta(seconds=timeout)
        self.unacknowledged_msgs[msg_id]['last_retry'] = self.unacknowledged_msgs[msg_id]['next_retry']
        self.unacknowledged_msgs[msg_id]['next_retry'] = ts.get_time_stamp(next_attempt)
        self.unacknowledged_msgs[msg_id]['retry_number'] = retry + 1

    def check_unacknowledged_msgs(self, zyre_msg):
        if zyre_msg.msg_content:
            contents = self.convert_zyre_msg_to_dict(zyre_msg.msg_content)
            ropod_msg_type = contents["header"]["type"]

        if ropod_msg_type == "ACKNOWLEDGEMENT":
            msg_id = contents["payload"]["receivedMsg"]
            self.logger.debug("Received acknowledgement from %s for %s!" % (zyre_msg.peer_name, msg_id))

            if msg_id in self.unacknowledged_msgs:
                # if no receiverIds were specified, accept any acknowledgement
                if not self.unacknowledged_msgs[msg_id]['receiverIds']:
                    self.unacknowledged_msgs.pop(msg_id)
                elif zyre_msg.peer_name in self.unacknowledged_msgs[msg_id]['receiverIds']:
                        peer_name = zyre_msg.peer_name
                        self.unacknowledged_msgs[msg_id]['receiverIds'].remove(peer_name)
                        # if all receiverIds have acknowledged
                        # print(self.unacknowledged_msgs[msg_id])
                        if not self.unacknowledged_msgs[msg_id]['receiverIds']:
                            self.logger.debug("All receiverIds have acknowledged message %s" % msg_id)
                            self.unacknowledged_msgs.pop(msg_id)

    def resend_message_cb(self):
        """
        This is a ROPOD specific function
        :return:
        """

        if not self.acknowledge:
            return

        dropped_msgs = []

        for msg_id, attempt_info in self.unacknowledged_msgs.items():
            if attempt_info['retry_number'] > self.number_of_retries:
                self.logger.warning("Retried {} times, stopping.".format(self.number_of_retries))
                dropped_msgs.append(msg_id)
            else:
                now = datetime.now().timestamp()
                if attempt_info['next_retry'] < now:
                    self.logger.debug("Attempt information: %s" % attempt_info)
                    msg_args = attempt_info['msg_args']
                    if attempt_info['zyre_msg_type'] == "SHOUT":
                        self.shout(**msg_args)
                    elif attempt_info['zyre_msg_type'] == "WHISPER":
                        self.whisper(**msg_args)
                    self.add_next_retry(msg_id)

        for msg in dropped_msgs:
            self.unacknowledged_msgs.pop(msg)

    def test(self):
        print(self.name())
        print(self.groups())
        print(self.peers())

        time.sleep(ZYRE_SLEEP_TIME)
        msg = {'header': {'type': 'TEST_MSG', 'msgId': generate_uuid()},
               'payload': {'msg': 'test'}}

        for group in self.own_groups():
            self.shout(msg, group)
            time.sleep(1)
        self.shout('hello')
        self.whisper(msg, "chat_tester")
        self.whisper(msg, ["chat_tester", "chat_tester"])


def main():
    logging.getLogger('pyre').setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    logging.basicConfig(format="%(asctime)s [%(name)-12.12s] [%(levelname)-5.5s]  %(message)s",
                        level=logging.DEBUG)

    node1 = RopodPyre('node1',
                                ["TEST-GROUP"],
                                ["TEST_MSG"],
                                True, acknowledge=True)
    node1.start()
    msg_id = generate_uuid()
    msg = {'header':
            {'type': 'TEST_MSG', 'msgId': msg_id, 'receiverIds':['node2', 'node3']},
           'payload':
           {'msg': 'test'}}

    node1.shout(msg)
    time.sleep(6)

    node2 = RopodPyre('node2',
                                ["TEST-GROUP"],
                                ["TEST_MSG"],
                                False, acknowledge=True)
    node3 = RopodPyre('node3',
                                ["TEST-GROUP"],
                                ["TEST_MSG"],
                                False, acknowledge=True)
    node2.start()
    node3.start()
    time.sleep(6)
    node1.shutdown()
    node2.shutdown()
    node3.shutdown()


if __name__ == '__main__':
    main()
