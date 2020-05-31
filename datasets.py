""" Include methods to prepare and write struct objects to csv files
"""

import csv


def flatten_dict(dict_input):
    """ Returns a dictionary without nested dictionaries
    """
    flattened_dict = dict()

    for key, value in dict_input.items():
        if isinstance(value, dict):
            new_keys = sorted(value.keys())
            for new_key in new_keys:
                entry = {key + '_' + new_key: value[new_key]}
                flattened_dict.update(entry)
        else:
            entry = {key: value}
            flattened_dict.update(entry)

    return flattened_dict


def keep_entry(dict_input, parent_key, child_keys):
    """ Args:
        dict_input
        parent_key  string
        child_keys  list of strings

    Keeps child_keys in dict_input and not other entries that start with the same parent_key
    """
    dict_output = dict()

    child_keys = [''.join((parent_key, '_', child_key)) for child_key in child_keys]

    for key, value in dict_input.items():
        if key.startswith(parent_key) and key not in child_keys:
            pass
        else:
            dict_output.update({key: value})

    return dict_output


def to_csv(list_dicts, file_name):
    ''' Exports a list of dictionaries to a csv file
    args: list_dicts    list of dictionaries to be exported
          file_name     name of the csv file
    '''
    # We assume that all the dictionaries have the same keys
    fieldnames = list_dicts[0].keys()

    with open(file_name, 'w') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames)
        dict_writer.writeheader()
        dict_writer.writerows(list_dicts)
