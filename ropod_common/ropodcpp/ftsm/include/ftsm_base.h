#include <chrono>
#include <thread>
#include <exception>
#include <sstream>
#include <algorithm>
#include <bsoncxx/builder/stream/document.hpp>
#include <bsoncxx/json.hpp>
#include <bsoncxx/string/to_string.hpp>
#include <json/json.h>

#include <mongocxx/client.hpp>
#include <mongocxx/instance.hpp>

#include "ftsm.h"

namespace ftsm
{
    struct DependMonitorTypes
    {
        static std::string HEARTBEAT;
        static std::string FUNCTIONAL;
    };

    struct MonitorConstants
    {
        static std::string NONE;
    };

    class FTSMBase : public FTSM
    {
    public:
        FTSMBase(const std::string &name, const std::vector<std::string> &dependencies,
                 const std::map<std::string, std::map<std::string, std::string>> &dependency_monitors={},
                 int max_recovery_attempts=1,
                 std::string robot_store_db_name="robot_store", int robot_store_db_port=27017,
                 std::string robot_store_component_collection="components",
                 std::string robot_store_status_collection="status",
                 std::string robot_store_sm_state_collection="component_sm_states",
                 bool debug=false);

        /**
         * Method for component initialisation
         */
        virtual std::string init();

        /**
         * Method for component configuration/reconfiguration
         */
        virtual std::string configuring();

        /**
         * Method for the behaviour of a component when it is ready for operation, but not active
         */
        virtual std::string ready();

        /**
         * Abstract method for the behaviour of a component during active operation
         */
        virtual std::string running() = 0;

        /**
         * Abstract method for component recovery
         */
        virtual std::string recovering() = 0;

        /**
         * Processes the statuses of the component dependencies and returns
         * a state transition string from FTSMTransitions (or "" if no transition
         * needs to take place.) The default implementation simply returns "".
         */
        virtual std::string processDependStatuses();

        /**
         * For ROS components, performs any necessary setup steps (initialising
         * a node, registering publishers/subscribers/services/action servers or clients).
         */
        virtual void setupRos() { }

        /**
         * For ROS components, performs any necessary cleanup steps when the ROS
         * master dies so that the component can recover itself when the master
         * comes back up (e.g. unregistering services).
         */
        virtual void tearDownRos() { }

        /*
         * For ROS components that have "roscore" listed as a **heartbeat** dependency,
         * recovers from a dead ROS master in case the master is dead.
         * self.tear_down_ros and self.setup_ros should be overridden for
         * the recovery to be actually performed.
         */
        void recoverFromPossibleDeadRosmaster();

        Json::Value convertStringToJson(const std::string &msg);
    protected:
        std::map<std::string, std::map<std::string, std::string>> dependency_monitors;

        std::string robot_store_db_name;

        int robot_store_db_port;

        std::string robot_store_component_collection;

        std::string robot_store_status_collection;

        std::string robot_store_sm_state_collection;

        /*
        A dictionary of the form
        {
            component_monitor_type
            {
                component_name
                {
                    monitor: status
                }
            }
        }

        Example:
        {
            functional
            {
                smart_wheel
                {
                    ros/smart_wheel_ethercat_parser: [status-msg]
                }
            }
        }
         */
        std::map<std::string, std::map<std::string, std::map<std::string, std::string>>> depend_statuses;

        typedef std::map<std::string, std::map<std::string, std::map<std::string, std::string>>>::const_iterator MonitorIterator;
        typedef std::map<std::string, std::map<std::string, std::string>>::const_iterator ComponentIterator;
        typedef std::map<std::string, std::string>::const_iterator MonitorSpecIterator;
    private:
        std::vector<std::string> getComponentDependencies(std::string component_name);

        std::map<std::string, std::map<std::string, std::string>> getDependencyMonitors(std::string component_name);

        void getDependencyStatuses();

        void writeSMState();

        std::thread depend_status_thread;

        std::thread sm_state_thread;

        bool debug;

        mongocxx::instance mongo_instance;
        mongocxx::client connection_;
    };
}
