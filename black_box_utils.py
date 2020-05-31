class BBUtils(object):
    '''A collection of methods for simplifying the interaction with a robot black box.

    Author -- Alex Mitrevski
    Contact -- aleksandar.mitrevski@h-brs.de

    '''
    @staticmethod
    def get_bb_id(robot_id):
        '''Extracts the ID of the robot and creates the ID of the black box
        corresponding to that robot. The robot ID is assumed to be in the form
        robot_<xxx>, where <xxx> is the actual ID and the resulting
        black box ID will have the form black_box_<xxx>

        Keyword arguments:
        robot_id -- ID of a robot

        '''
        robot_number = robot_id[robot_id.rfind('_')+1:]
        black_box_id = 'black_box_{0}'.format(robot_number)
        return black_box_id

    @staticmethod
    def get_robot_id(black_box_id):
        '''Extracts the ID of the black box and creates the ID of the robot
        corresponding to that black box. The black box ID is assumed to be in the form
        black_box_<xxx>, where <xxx> is the actual ID and the resulting
        robot ID will have the form robot_<xxx>

        Keyword arguments:
        black_box_id -- ID of a black box

        '''
        black_box_number = black_box_id[black_box_id.rfind('_')+1:]
        robot_id = 'robot_{0}'.format(black_box_number)
        return robot_id
