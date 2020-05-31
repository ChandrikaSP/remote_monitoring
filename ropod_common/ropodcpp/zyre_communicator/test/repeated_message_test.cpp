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
    : ZyreBaseCommunicator(nodeName, printAllReceivedMessages, interface, acknowledge)
    {};

    private:
    virtual void recvMsgCallback(ZyreMsgContent* msgContent);
    virtual void sendMessageStatusCallback(const std::string &msgId, bool status);
};

void ZyreNode::recvMsgCallback(ZyreMsgContent* msgContent)
{
    if (msgContent->event == "SHOUT" or msgContent->event == "WHISPER")
    {
        std::cout << "successfully received message from " << msgContent->peer << std::endl;
    }
    //std::cout << this->getNodeName() << " received message" << "\n";
    //std::cout << message << "\n";
}

void ZyreNode::sendMessageStatusCallback(const std::string &msgId, bool status)
{
}

std::string getMessage(const std::string &message_type)
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

    msg["payload"]["metamodel"] = "none";
    msg["payload"]["msg"] = "empty";

    std::stringstream jsonMsg("");
    jsonMsg << msg;
    return jsonMsg.str();
}

int main(int argc, char *argv[])
{
    std::vector<std::string> groups;
    groups.push_back("group1");
    bool b = true;

    ZyreNode node_1("ZyreNode_test_1", b, "", false);
    ZyreNode node_2("ZyreNode_test_2", b, "", false);
    node_1.joinGroup(groups);
    node_2.joinGroup(groups);

    std::string msg1 = getMessage("TASK");
    std::string msg2 = getMessage("TASK-REQUEST");

    // shout a TASK message; node_2 should accept it
    node_1.shout(msg1, "group1");
    zclock_sleep(500);
    // reshout same message; node_2 should reject it
    node_1.shout(msg1, "group1");
    zclock_sleep(2000);
    // shout new message; node_2 should accept it
    node_1.shout(msg2, "group1");

    zclock_sleep(1000);
    std::cout << std::endl << "waiting for 30 seconds..." << std::endl << std::endl;
    zclock_sleep(30000);
    // shout message again after validity expires; node_2 should accept it
    node_1.shout(msg1, "group1");

    zclock_sleep(500);

    return 0;
}
