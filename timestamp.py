
import dateutil.parser
from datetime import timezone, datetime, timedelta


class TimeStamp:
    """A timestamp object that supports some of the operations of datetime objects.

    Args:
        delta: Can be an object of type datetime.timedelta or TimeStamp
    """

    def __init__(self, delta=None):
        """Constructor of the TimeStamp object.

        This creates an abstraction of a datetime.datetime.now() object

        Args:
            delta (timedelta): A timedelta object to be added to datetime.now()
        """
        self._time = datetime.now()
        if delta is not None:
            self._time = self._time + delta

    def __add__(self, delta):
        if isinstance(delta, timedelta):
            return TimeStamp.from_datetime(self._time + delta)
        else:
            raise Exception("delta must be an object of datetime.timedelta.")

    def __sub__(self, delta):
        if isinstance(delta, timedelta):
            return TimeStamp.from_datetime(self._time - delta)
        # if isinstance(delta, TimeStamp):
        #     return self._time - delta._time
        else:
            raise Exception("delta must be an object of datetime.timedelta.")

    def __gt__(self, other):
        return self._time > other._time

    def __lt__(self, other):
        return self._time < other._time

    def __ge__(self, other):
        return self._time >= other._time

    def __le__(self, other):
        return self._time <= other._time

    def __str__(self):
        return self._time.isoformat()

    def __repr__(self):
        return "TimeStamp(%s)" % self._time.isoformat()

    @property
    def timestamp(self):
        return self._time.timestamp()

    @timestamp.setter
    def timestamp(self, value):
        if not isinstance(value, datetime):
            raise Exception("value must be an object of datetime.datetime")

        self._time = value

    def to_str(self):
        """Returns the timestamp as a string in ISO format"""
        return self._time.isoformat()

    def get_difference(self, other, resolution=None):
        """Returns the difference between itself and another TimeStamp object

        Args:
            other: timedelta or TimeStamp object
            resolution (str): the desired resolution of the result.
                    It can either be "hours" or "minutes".
                    If no valid resolution is specified, it will return the timedelta object.
        Returns:
            timedelta object or float number depending on the specified resolution.
        """
        _res = {'hours': 3600, 'minutes': 60, 'seconds': 1}.get(resolution)

        if isinstance(other, TimeStamp):
            result = self._time - other._time
        else:
            raise Exception("Object must be of TimeStamp type")

        if resolution in ['hours', 'minutes', 'seconds']:
            return result.total_seconds() / _res
        else:
            return result

    @classmethod
    def from_datetime(cls, datetime):
        x = cls()
        x._time = datetime
        return x

    @classmethod
    def from_str(cls, iso_date):
        t = dateutil.parser.parse(iso_date)
        return cls.from_datetime(t)

    def to_datetime(self):
        return self._time
