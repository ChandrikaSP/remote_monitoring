#ifndef ZYREBASECOMMUNICATOR_H
#define ZYREBASECOMMUNICATOR_H

#include<zyre.h>
#include<string>
#include<vector>
#include <json/json.h>
#include <ctime>
#include <utility>
#include <mutex>

struct ZyreParams
{
    std::string nodeName;
    std::vector<std::string> groups;
};

struct Peer
{
    std::string name;
    std::string id;
    std::string address;
};

struct ZyreMsgContent
{
    std::string event;
    std::string peer;
    std::string name;
    std::string group;
    std::string message;
};

/**
 * Defines parameters used in the queuing and resending
 * of messages that require an acknowledgement to be received
 */
struct ResendMessageParams
{
    /*
     * number of times left to retry sending message
     */
    int number_of_retries_left;
    /*
     * Next Unix timestamp after which to retry sending message
     */
    double next_retry_time;
    /*
     * True if method for sending is shout,
     * False if method for sending is whisper
     */
    bool is_shout;
    /*
     * If method is shout, the group to shout to
     */
    std::string group;
    /*
     * If method is whisper, the peer to whisper to
     */
    std::string peer;
    /**
     * list of receiverIds from whom we are yet to receive an acknowledgement
     */
    std::vector<std::string> receiverIds;
};

class ZyreBaseCommunicator {
    public:
    /**
     * nodeName: name of zyre node
     * groups: list of groups to join if startImmediately is true
     * printAllReceivedMessages: prints all received events for debugging purposes
     * interface: network interface to use (if blank, zyre decides which one)
     * acknowledge: if true, messages that require acknowledgement will be acknowledged
     * startImmediately: if true, the node will start in the constructor (this means headers cannot be set)
     */
    ZyreBaseCommunicator(const std::string &nodeName,
	    const bool &printAllReceivedMessages,
        const std::string& interface="",
        bool acknowledge = false,
        bool startImmediately=true);
    ~ZyreBaseCommunicator();

    /**
     * start the zyre node and join specified groups
     */
    void startZyreNode();
    void setHeaders(const std::map<std::string, std::string> &headers);
    void shout(const std::string &message);
    void shout(const std::string &message, const std::string &group);
    void shout(const std::string &message, const std::vector<std::string> &groups);
    void whisper(const std::string &message, const std::string &id);
    void whisper(const std::string &message, const std::vector<std::string> &ids);
    void joinGroup(const std::string &group);
    void joinGroup(const std::vector<std::string> &groups);
    void leaveGroup(const std::string &group);
    void leaveGroup(std::vector<std::string> groups);

    /**
     * sets the types of messages for which this node expects an acknowledgement
     */
    void setExpectAcknowledgementFor(const std::vector<std::string> &messageTypes);
    /**
     * sets the types of messages for which this node will send back an
     * acknowledgement when received
     */
    void setSendAcknowledgementFor(const std::vector<std::string> &messageTypes);

    std::string getNodeName() {return params.nodeName;}
    std::vector<std::string> getJoinedGroups() {return params.groups;}
    ZyreParams getZyreParams() {return params;}
    void printNodeName();
    void printJoinedGroups();
    void printZyreMsgContent(const ZyreMsgContent &msgContent);
    std::string getTimeStamp();

    /**
     * Called when an incoming message is received
     */
    virtual void recvMsgCallback(ZyreMsgContent* msgContent) = 0;
    /**
     * Called when an outgoing message has either been acknowledged or
     * the maximum number of retries has been exceeded
     *
     * @param msgId the message ID of the outgoing message
     * @param status True if acknowledged, False if retries exceeded
     */
    virtual void sendMessageStatus(const std::string &msgId, bool status) {}
    Json::Value convertZyreMsgToJson(ZyreMsgContent* msg_params);
    Json::Value convertStringToJson(const std::string &msg);
    std::string convertJsonToString(const Json::Value &root);
    std::string generateUUID();

    /**
     * Checks if any messages in the queue need to be resent because no acknowledgement
     * for them has been received, and resends them
     */
    void resendMessages();
    /**
     * Processes an incoming acknowledgement to remove the respective messages from the resend queue
     */
    void processAcknowledgement(ZyreMsgContent *msgContent);

    /**
     * map from msgId to (msg, parameters for resending)
     */
    typedef std::map<std::string, std::pair<std::string, ResendMessageParams> > MessageQueue;
    /**
     * map from msgId to arrival time of message in ms
     */
    typedef std::map<std::string, double> ReceivedMessages;

    private:
    ZyreParams params;
    zyre_t *node;
    zactor_t* receiveActor;
    bool printAllReceivedMessages;
    const int ZYRESLEEPTIME = 500;
    static const int ZYREPOLLTIME = 1000;
    Json::StreamWriterBuilder json_stream_builder_;
    bool acknowledge;
    /**
     * message types for which an acknowledgement is requested
     * i.e. when this node shouts or whispers these message types,
     * it expects an acknowledgement in return
     */
    std::vector<std::string> expectAcknowledgementFor;
    /**
     * message types for which an acknowledgement needs to be sent
     * i.e. when this node receives these message types,
     * it will send an acknowledgement in return
     */
    std::vector<std::string> sendAcknowledgementFor;

    /**
     * Queue of messages which are awaiting acknowledgement
     */
    MessageQueue messageQueue;
    /**
     * Mutex to protect read/write to message queue
     */
    std::mutex messageQueueMutex;
    // interval between resending messages in ms
    int messageInterval;

    // number of times to retry sending messages
    int numRetries;

    /**
     * maximum time after arrival in ms during which a message is considered valid
     * i.e. any message received with the same msgId will be discarded during the
     * validity period of a message
     */
    double maxMessageAge;

    /**
     * list of recently received messages
     * this is used to discard repeated messages
     */
    ReceivedMessages receivedMessages;

    /**
     * Returns the current time in ms
     */
    double getCurrentTime();
    static void receiveLoop(zsock_t* pipe, void* args);
    zmsg_t* stringToZmsg(std::string msg);
    ZyreMsgContent* zmsgToZyreMsgContent(zmsg_t *msg);

    /**
     * Returns true if this message has already been received in the near past
     * The near past is defined by maxMessageAge in ms
     *
     * if the message has not been received already, it is added to the 
     * list of receivedMessages
     */
    bool isMessageRepeated(ZyreMsgContent *msgContent);

    /**
     * sends an acknowledgement for an incoming message if required
     */
    void sendAcknowledgement(ZyreMsgContent * msgContent);
    /**
     * checks if this message is one that we expect an acknowledgement for
     */
    bool requiresAcknowledgement(const Json::Value &root);
    /**
     * Queue messages until an acknowledgement is received
     */
    void addMessageToQueue(const std::string &msgId, const std::string &message, const std::string &group_or_peer, bool is_shout, const std::vector<std::string> &receiverIds);
    /**
     * check if message requires acknowledgement and add to the queue if necessary
     */
    void checkAndQueueMessage(const std::string &message, const std::string &group_or_peer, bool is_shout);
};

#endif
