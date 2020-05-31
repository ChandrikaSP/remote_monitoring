#include "ZyreBaseCommunicator.h"
#include <json/json.h>
#include <iostream>
#include <sstream>

class ZyreNode : public ZyreBaseCommunicator
{
    public:
    ZyreNode(const std::string &nodeName,
	    const bool &printAllReceivedMessages,
        const std::string &interface="",
        bool acknowledge = false)
    : ZyreBaseCommunicator(nodeName, printAllReceivedMessages, interface, acknowledge, false)
    {
        std::map<std::string, std::string> headers;
        headers["name"] = nodeName;
        setHeaders(headers);
        startZyreNode();
    };

    private:
    virtual void recvMsgCallback(ZyreMsgContent* msgContent);
    virtual void sendMessageStatus(const std::string &msgId, bool status);
};

void ZyreNode::recvMsgCallback(ZyreMsgContent* msgContent)
{
    //std::cout << this->getNodeName() << " received message" << "\n";
    //std::cout << message << "\n";
}

void ZyreNode::sendMessageStatus(const std::string &msgId, bool status)
{
    std::cout << "Got send status for " << msgId << ": " << status << std::endl;
}

std::string getMessage(const std::string &message_type, const std::vector<std::string> &recipients)
{
    Json::Value msg;
    msg["header"]["type"] = message_type;
    msg["header"]["metamodel"] = "ropod-msg-schema.json";
    zuuid_t * uuid = zuuid_new();
    const char * uuid_str = zuuid_str_canonical(uuid);
    msg["header"]["msgId"] = uuid_str;
    zuuid_destroy (&uuid);
    char *timestr = zclock_timestr (); // TODO: this is not ISO 8601
    msg["header"]["timestamp"] = timestr;
    zstr_free(&timestr);

    for (int i = 0; i < recipients.size(); i++)
    {
        msg["header"]["recipients"][i] = recipients[i];
    }

    msg["payload"]["metamodel"] = "none";
    msg["payload"]["msg"] = "empty";

    std::stringstream jsonMsg("");
    jsonMsg << msg;
    std::cout << "msg: " << jsonMsg.str() << std::endl;
    return jsonMsg.str();
}

int main(int argc, char *argv[])
{
    std::vector<std::string> messageTypes;
    messageTypes.push_back("TASK");
    messageTypes.push_back("TASK-REQUEST");

    std::vector<std::string> acknowledgeMessageTypes;
    acknowledgeMessageTypes.push_back("TASK");
    acknowledgeMessageTypes.push_back("TASK-REQUEST");

    std::vector<std::string> groups;
    groups.push_back("group1");
    bool b = true;

    ZyreNode node_1("ZyreNode_test_1", b, "", true);
    node_1.joinGroup(groups);
    node_1.setExpectAcknowledgementFor(acknowledgeMessageTypes);
    node_1.setSendAcknowledgementFor(messageTypes);
    ZyreNode node_2("ZyreNode_test_2", b, "", false);
    node_2.joinGroup(groups);
    node_2.setExpectAcknowledgementFor(acknowledgeMessageTypes);
    node_2.setSendAcknowledgementFor(messageTypes);

    std::vector<std::string> recipients = {"ZyreNode_test_3", "ZyreNode_test_4"};
    std::string msg1 = getMessage("TASK", recipients);

    // shout a TASK message expecting an acknowledgement
    node_1.shout(msg1, "group1");
    // since node_2 does not acknowledge messages, node_1 will retry
    zclock_sleep(6000);

    // node_3 will now respond with an acknowledgement on the
    // next message received
    ZyreNode node_3("ZyreNode_test_3", b, "", true);
    node_3.joinGroup(groups);
    node_3.setExpectAcknowledgementFor(acknowledgeMessageTypes);
    node_3.setSendAcknowledgementFor(messageTypes);

    // since we're still waiting for node_4 to acknowledge, node_1 will retry
    zclock_sleep(6000);
    // node_4 will now respond with an acknowledgement on the
    // next message received
    ZyreNode node_4("ZyreNode_test_4", b, "", true);
    node_4.joinGroup(groups);
    node_4.setExpectAcknowledgementFor(acknowledgeMessageTypes);
    node_4.setSendAcknowledgementFor(messageTypes);

    // once acknowledgement is received, node_1 stops resending stuff
    zclock_sleep(8000);

    return 0;
}
