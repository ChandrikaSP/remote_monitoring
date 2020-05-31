#include "ZyreBaseCommunicator.h"
#include <iostream>
#include <cstdarg>
#include <algorithm>  // provides std::find
#include <sstream>
#include <tuple>
#include <chrono>

ZyreBaseCommunicator::ZyreBaseCommunicator(const std::string &nodeName,
		 const bool &printAllReceivedMessages,
         const std::string& interface,
         bool acknowledge,
         bool startImmediately)
{
    this->params.nodeName = nodeName;
    this->printAllReceivedMessages = printAllReceivedMessages;
    this->params.groups = std::vector<std::string> {};  // will be filled by this->joinGroup()
    this->acknowledge = acknowledge;
    // TODO: this needs to be specified for each message type
    this->messageInterval = 5000;
    // TODO: ensure messageInterval * numRetries < maxMessageAge
    // so that nodes who have already sent an acknowledgement don't
    // process repeated messages
    this->numRetries = 5;
    // if same msgId received within 30 seconds, discard it
    this->maxMessageAge = 30000;

    this->node = zyre_new(nodeName.c_str());
    if (!node)
        return;                 //  Could not create new node
    if (interface != "")
    {
        zyre_set_interface (node, interface.c_str());
    }
    if (startImmediately)
    {
        this->startZyreNode();
    }

}

ZyreBaseCommunicator::~ZyreBaseCommunicator()
{
    leaveGroup(params.groups);
    zactor_destroy(&receiveActor);
    zyre_stop(node);
    zclock_sleep(this->ZYRESLEEPTIME);
    zyre_destroy(&node);
}

void ZyreBaseCommunicator::startZyreNode()
{
    zyre_start(this->node);
    zclock_sleep(this->ZYRESLEEPTIME);

    receiveActor = zactor_new(receiveLoop, this);
    assert(receiveActor);
}

void ZyreBaseCommunicator::setHeaders(const std::map<std::string, std::string> &headers)
{
    std::map<std::string, std::string>::const_iterator it;
    for (it = headers.begin(); it != headers.end(); ++it)
    {
        zyre_set_header(this->node, it->first.c_str(), "%s", it->second.c_str());
    }
}

void ZyreBaseCommunicator::printNodeName()
{
    std::cout << "nodeName: " << params.nodeName << std::endl;
}

void ZyreBaseCommunicator::printJoinedGroups()
{
    std::stringstream msg;
    msg << params.nodeName << "--- Printing joined groups: " << "\n";
    for (auto it = params.groups.begin(); it != params.groups.end(); it++)
    {
	    msg << "    " << *it << "\n";
    }
    msg << "\n";
    std::cout << msg.rdbuf();
}

void ZyreBaseCommunicator::receiveLoop(zsock_t *pipe, void *args)
{
    ZyreBaseCommunicator* objectPtr = (ZyreBaseCommunicator*) args;
    zsock_signal (pipe, 0);     //  Signal "ready" to caller

    // wait a bit for constructor to finish
    // this is required because we don't want to call recvMsgCallback
    // which is a pure virtual function from the base class constructor
    zclock_sleep(500);

    bool terminated = false;
    zpoller_t *poller = zpoller_new (pipe, zyre_socket (objectPtr->node), NULL);
    while (!terminated) {
        // this will return either when a new message is received or when timeout expires
        void *which = zpoller_wait (poller, ZyreBaseCommunicator::ZYREPOLLTIME);
        // expired due to process termination
        if (zpoller_terminated(poller))
        {
            terminated = true;
            break;
        }
        else if (which == pipe)
        {
            zmsg_t* msg = zmsg_recv (which);
            if (!msg)
                break;              //  Interrupted

            char *command = zmsg_popstr (msg);
            if (streq (command, "$TERM"))
                terminated = true;
            else {
                puts ("E: invalid message to receiveActor");
                assert (false);
            }
            free (command);
            zmsg_destroy (&msg);
        }
        else if (which == zyre_socket (objectPtr->node))
        {
            zmsg_t *msg = zmsg_recv (which);
            ZyreMsgContent* msgContent = objectPtr->zmsgToZyreMsgContent(msg);
            zmsg_destroy (&msg);

            if ((objectPtr->printAllReceivedMessages) and (msgContent->event != "EVASIVE"))
            {
                std::stringstream out_msg;
                out_msg << "---- " << objectPtr->params.nodeName << " Received Message -----" << std::endl;
                out_msg << "Event: " << msgContent->event << "\n";
                out_msg << "Peer: " <<  msgContent->peer << "\n";
                out_msg << "Name: " <<  msgContent->name << "\n";
                out_msg << "Group: " << msgContent->group << "\n";
                out_msg << "Message: " <<  msgContent->message << "\n\n";
                std::cout <<  out_msg.rdbuf();
            }
            if ((msgContent->event == "SHOUT" || msgContent->event == "WHISPER"))
            {
                // if shout or whisper only call the callback if message is not repeated
                if (!objectPtr->isMessageRepeated(msgContent))
                {
                    // check if we need to send an acknowledgement
                    objectPtr->sendAcknowledgement(msgContent);

                    if (msgContent->event == "WHISPER")
                    {
                        // we may have received an acknowledgement, so process it
                        objectPtr->processAcknowledgement(msgContent);
                    }
                    objectPtr->recvMsgCallback(msgContent);
                }
            }
            else // any other type of event, call the callback anyway
            {
                objectPtr->recvMsgCallback(msgContent);
            }
        }
        // resend any messages in the queue
        objectPtr->resendMessages();
    }
    zpoller_destroy (&poller);
}

void ZyreBaseCommunicator::sendAcknowledgement(ZyreMsgContent * msgContent)
{
    if (!acknowledge)
    {
        return;
    }
    if (!msgContent->message.empty())
    {
        Json::Value root = convertZyreMsgToJson(msgContent);
        if (root.isMember("header") && root["header"].isMember("type")
            && root["header"].isMember("msgId"))
        {
            if (root["header"].isMember("receiverIds"))
            {
                bool is_self_receiver = false;
                Json::ArrayIndex size = root["header"]["receiverIds"].size();
                for (Json::ArrayIndex i = 0; i < size; i++)
                {
                    std::string receiverId = root["header"]["receiverIds"][i].asString();
                    if (receiverId == this->params.nodeName)
                    {
                        is_self_receiver = true;
                        break;
                    }
                }
                if (!is_self_receiver)
                {
                    return;
                }
            }
            std::string msg_type = root["header"]["type"].asString();
            // only acknowledge known message types
            if (std::find(std::begin(sendAcknowledgementFor),
                std::end(sendAcknowledgementFor), msg_type) != std::end(sendAcknowledgementFor))
            {
                Json::Value ack_msg;
                ack_msg["header"]["type"] = "ACKNOWLEDGEMENT";
                ack_msg["header"]["metamodel"] = "ropod-msg-schema.json";
                ack_msg["header"]["msgId"] = generateUUID();
                char *timestr = zclock_timestr (); // TODO: this is not ISO 8601
                ack_msg["header"]["timestamp"] = timestr;
                zstr_free(&timestr);
                ack_msg["payload"]["receivedMsg"] = root["header"]["msgId"].asString();
                std::string ack_msg_str = convertJsonToString(ack_msg);
                whisper(ack_msg_str, msgContent->peer);
            }
        }
    }
}

zmsg_t* ZyreBaseCommunicator::stringToZmsg(std::string msg)
{
    zmsg_t* message = zmsg_new();
    zframe_t *frame = zframe_new(msg.c_str(), msg.size());
    zmsg_prepend(message, &frame);
    return message;
}

void ZyreBaseCommunicator::shout(const std::string &message, const std::vector<std::string> &groups)
{
    // TODO: check if subscribed to group
    for (auto it = groups.begin(); it != groups.end(); it++)
    {
	    shout(message, *it);
    }
}

void ZyreBaseCommunicator::shout(const std::string &message)
{
    for (auto it = params.groups.begin(); it != params.groups.end(); it++)
    {
        shout(message, *it);
    }
}

void ZyreBaseCommunicator::shout(const std::string &message, const std::string &group)
{
    checkAndQueueMessage(message, group, true);
    zyre_shouts(node, group.c_str(), "%s", message.c_str());
}


void ZyreBaseCommunicator::whisper(const std::string &message, const std::string &peer)
{
    checkAndQueueMessage(message, peer, false);
    zyre_whispers(node, peer.c_str(), "%s", message.c_str());
}

void ZyreBaseCommunicator::whisper(const std::string &message, const std::vector<std::string> &peers)
{
    for (auto it = peers.begin(); it != peers.end(); ++it)
    {
        whisper(message, *it);
    }
}

void ZyreBaseCommunicator::joinGroup(const std::string &group)
{
    auto it = std::find(params.groups.begin(), params.groups.end(), group);
    if (it == params.groups.end())  // if node is not subscribed to group
    {
	    zyre_join(node, group.c_str());
	    params.groups.push_back(group);
        zclock_sleep(this->ZYRESLEEPTIME);
    }
    else
    {
	    std::cout << "Trying to join: " << group << " but already joined... Doing nothing!" << std::endl;
    }
}

void ZyreBaseCommunicator::joinGroup(const std::vector<std::string> &groups)
{
    for (auto it = groups.begin(); it != groups.end(); it++)
    {
	    joinGroup(*it);
    }
}

void ZyreBaseCommunicator::leaveGroup(const std::string &group)
{
    leaveGroup(std::vector<std::string> {group});
}

void ZyreBaseCommunicator::leaveGroup(std::vector<std::string> groups)
{
    for (auto it = groups.begin(); it != groups.end(); it++)
    {
        auto paramsGroupPtr = std::find(params.groups.begin(), params.groups.end(), *it);
        if (paramsGroupPtr != params.groups.end())
        {
            zyre_leave(node, (*it).c_str());
            params.groups.erase(paramsGroupPtr);
        }
        else
        {
            // TODO: make this more sophisticated. Issue BlackBox?
            std::stringstream msg;
            msg << params.nodeName << " trying to leave group " << *it << " but node not in that group... Doing nothing!" << "\n";
            std::cout << msg.rdbuf();
        }
    }
}

void ZyreBaseCommunicator::setExpectAcknowledgementFor(const std::vector<std::string> &messageTypes)
{
    expectAcknowledgementFor = messageTypes;
}

void ZyreBaseCommunicator::setSendAcknowledgementFor(const std::vector<std::string> &messageTypes)
{
    sendAcknowledgementFor = messageTypes;
}

bool ZyreBaseCommunicator::requiresAcknowledgement(const Json::Value &root)
{
    if (root.isMember("header")  &&
        root["header"].isMember("msgId") &&
        root["header"].isMember("type"))
    {
        std::string type = root["header"]["type"].asString();
        if (std::find(std::begin(expectAcknowledgementFor), std::end(expectAcknowledgementFor), type) != std::end(expectAcknowledgementFor))
        {
            return true;
        }
    }
    return false;
}

void ZyreBaseCommunicator::addMessageToQueue(const std::string &msgId, const std::string &message, const std::string &group_or_peer, bool is_shout, const std::vector<std::string> &receiverIds)
{
    double current_time_ms = getCurrentTime();
    current_time_ms += messageInterval;

    ResendMessageParams resend_params;
    resend_params.number_of_retries_left = this->numRetries;
    resend_params.next_retry_time = current_time_ms;
    resend_params.is_shout = is_shout;
    resend_params.receiverIds = receiverIds;
    if (is_shout)
    {
        resend_params.group = group_or_peer;
    }
    else
    {
        resend_params.peer = group_or_peer;
    }

    auto item = std::make_pair(message, resend_params);

    std::lock_guard<std::mutex> guard(messageQueueMutex);
    messageQueue[msgId] = item;
}

void ZyreBaseCommunicator::checkAndQueueMessage(const std::string &message, const std::string &group_or_peer, bool is_shout)
{
    Json::Value root = convertStringToJson(message);
    if (requiresAcknowledgement(root))
    {
        std::string msgId = root["header"]["msgId"].asString();
        std::vector<std::string> receiverIds;
        if (root["header"].isMember("receiverIds"))
        {
            Json::ArrayIndex size = root["header"]["receiverIds"].size();
            for (Json::ArrayIndex i = 0; i < size; i++)
            {
                std::string receiverId = root["header"]["receiverIds"][i].asString();
                receiverIds.push_back(receiverId);
            }
        }
        std::cout << msgId << " requires acknowledgement; adding to queue" << std::endl;
        addMessageToQueue(msgId, message, group_or_peer, is_shout, receiverIds);
    }
}

void ZyreBaseCommunicator::resendMessages()
{
    double current_time_ms = getCurrentTime();
    MessageQueue::iterator it;

    // protect the messageQueue since we might delete items from it
    std::lock_guard<std::mutex> guard(messageQueueMutex);
    for (it = messageQueue.begin(); it != messageQueue.end();)
    {
        double resend_time = it->second.second.next_retry_time;
        bool deleted = false;
        if (resend_time < current_time_ms)
        {
            std::cout << "Resending message: " << it->first << std::endl;
            std::cout << "Retries left: " << it->second.second.number_of_retries_left << std::endl;
            // resend the message
            std::string message = it->second.first;
            if (it->second.second.is_shout)
            {
                std::string group = it->second.second.group;
                zyre_shouts(node, group.c_str(), "%s", message.c_str());
            }
            else
            {
                std::string peer = it->second.second.peer;
                zyre_whispers(node, peer.c_str(), "%s", message.c_str());
            }
            // set next send time
            it->second.second.next_retry_time += messageInterval;
            // decrement resend count
            it->second.second.number_of_retries_left -= 1;
            // if we've sent enough times, remove it from the cache
            if (it->second.second.number_of_retries_left == -1)
            {
                std::string msgId = it->first;
                messageQueue.erase(it++);
                deleted = true;
                this->sendMessageStatus(msgId, false);
            }
        }
        if (!deleted)
        {
            ++it;
        }
    }
}

void ZyreBaseCommunicator::processAcknowledgement(ZyreMsgContent *msgContent)
{
    Json::Value root = convertStringToJson(msgContent->message);
    if (root.isMember("header") &&
        root["header"].isMember("type") &&
        root["header"]["type"].asString() == "ACKNOWLEDGEMENT")
    {
        std::lock_guard<std::mutex> guard(messageQueueMutex);

        std::string msgId = root["payload"]["receivedMsg"].asString();
        std::string peer = msgContent->peer;
        std::cout << "Received acknowledgement for for msgid " << msgId << " from " << peer << std::endl;
        auto it = messageQueue.find(msgId);
        if (it != messageQueue.end())
        {
            // no receiverIds specified, so accept any acknowledgement
            if (it->second.second.receiverIds.empty())
            {
                std::cout << "All acknowledgements received" << std::endl;
                messageQueue.erase(it);
                this->sendMessageStatus(msgId, true);
            }
            else
            {
                char * name = zyre_peer_header_value(this->node, peer.c_str(), "name");
                std::string name_str(name);
                auto &receiverIds = it->second.second.receiverIds;
                auto recp_it = std::find(receiverIds.begin(), receiverIds.end(), name_str);
                if (recp_it != receiverIds.end())
                {
                    std::cout << "Accepted acknowledgement from " << peer << " (" << name_str << ")" << std::endl;
                    it->second.second.receiverIds.erase(recp_it);
                    // if we've received acknowledgements from all receiverIds
                    if (it->second.second.receiverIds.empty())
                    {
                        std::cout << "All acknowledgements received" << std::endl;
                        messageQueue.erase(it);
                        this->sendMessageStatus(msgId, true);
                    }
                }
                free(name);
            }

        }
    }
}

bool ZyreBaseCommunicator::isMessageRepeated(ZyreMsgContent *msgContent)
{
    // remove old messages
    ReceivedMessages::iterator it;
    double currentTime = getCurrentTime();
    for (it = receivedMessages.begin(); it != receivedMessages.end();)
    {
        if (it->second + maxMessageAge  < currentTime)
        {
            //message has expired, so delete it
            receivedMessages.erase(it++);
        }
        else
        {
            ++it;
        }
    }
    // check if received message is a repeated one
    Json::Value root = convertStringToJson(msgContent->message);
    if (root.isMember("header") &&
        root["header"].isMember("type") &&
        root["header"].isMember("msgId"))
    {
        std::string msgId = root["header"]["msgId"].asString();
        if (receivedMessages.count(msgId) != 0)
        {
            std::cout << "Received repeated message " << msgId << ". Discarding it." << std::endl;
            return true;
        }
        else
        {
            receivedMessages[msgId] = currentTime;
        }
    }
    return false;
}

double ZyreBaseCommunicator::getCurrentTime()
{
    using namespace std::chrono;
    double current_time_ms = duration_cast<milliseconds>(system_clock::now().time_since_epoch()).count();
    return current_time_ms;
}

ZyreMsgContent* ZyreBaseCommunicator::zmsgToZyreMsgContent(zmsg_t *msg)
{
    std::string sevent, speer, sname, sgroup, smessage;
    char *event, *peer, *name, *group, *message;
    event = zmsg_popstr(msg);
    peer = zmsg_popstr(msg);
    name = zmsg_popstr(msg);
    group = zmsg_popstr(msg);
    message = zmsg_popstr(msg);

    sevent = (event == nullptr) ? "" : event;
    speer = (peer == nullptr) ? "" : peer;
    sname = (name == nullptr) ? "" : name;
    if (sevent == "WHISPER")
    {
        // if event is whisper, the group is empty
        // and the message is the fourth item to be popped
        sgroup = "";
        smessage = (group == nullptr) ? "" : group;
    }
    else
    {
        sgroup = (group == nullptr) ? "" : group;
        smessage = (message == nullptr) ? "" : message;
    }

    free(event);
    free(peer);
    free(name);
    free(group);
    free(message);

    ZyreMsgContent* msg_params = new ZyreMsgContent{sevent, speer, sname, sgroup, smessage};
    return msg_params;
}

/**
  * Converts msg_params.message to a json message
  *
  * @param msg_params message data
  */
Json::Value ZyreBaseCommunicator::convertZyreMsgToJson(ZyreMsgContent* msg_params)
{
    return convertStringToJson(msg_params->message);
}

Json::Value ZyreBaseCommunicator::convertStringToJson(const std::string &msg)
{
    std::stringstream msg_stream;
    msg_stream << msg;

    Json::Value root;
    Json::CharReaderBuilder reader_builder;
    std::string errors;
    // TODO: handle exceptions
    bool ok = Json::parseFromStream(reader_builder, msg_stream, &root, &errors);

    return root;
}

std::string ZyreBaseCommunicator::convertJsonToString(const Json::Value &root)
{
    std::string msg = Json::writeString(json_stream_builder_, root);
	return msg;
}

std::string ZyreBaseCommunicator::generateUUID()
{
    zuuid_t *uuid = zuuid_new();
    const char *uuid_cstr = zuuid_str_canonical(uuid);
    std::string uuid_str(uuid_cstr);
    zuuid_destroy(&uuid);
    return std::string(uuid_str);
}

void ZyreBaseCommunicator::printZyreMsgContent(const ZyreMsgContent &msgContent)
{

}

std::string ZyreBaseCommunicator::getTimeStamp()
{
	time_t now;
    time(&now);
    char buffer[20];
    strftime(buffer, 20, "%FT%TZ", gmtime(&now));
    return std::string(buffer);
}
