from datetime import datetime, timedelta
from copy import copy
from argparse import Namespace


def get_end_of_month(date):
    nm = datetime(year=date.year, month=date.month, day=1) + timedelta(days=32)
    return datetime(year=nm.year, month=nm.month, day=1) - timedelta(days=1)


class IntervalTracker:
    """
    Group time-based data by Interval (year, month, day, hour, minute).

    To use, you .add() to the class as you read in time-tracked data.  When done,
    you .make() it to copy the data to arrays.

    If values are numeric, it will sum.  If not, will keep latest.
    """

    intervals_allowed = {'year': ['year', 'yearly', 'yr', 'annual'],
                         'month': ['month', 'monthly', 'mon', 'mn'],
                         'day': ['day', 'daily', 'dy'],
                         'hour': ['hour', 'hourly', 'hr'],
                         'minute': ['minute', 'min']}

    def __init__(self, interval, variables='value'):
        """
        Parameters
        ----------
        interval : str
            One of the self.intervals_allowed values.
        variables : str or list of str
            Variable name or list of variable names.  If .add'd by a list, the order
            presented here is utilized.
        """
        for itvname, itvlist in self.intervals_allowed.items():
            if interval.lower() in itvlist:
                self.interval = itvname
                break
        self.values = {}
        self.per_interval = {}
        if isinstance(variables, str):
            self.variables = [variables]
        elif isinstance(variables, (list, tuple)):
            self.variables = variables
        else:
            raise ValueError('Variables must be a string or list of strings.')
        for variable in self.variables:
            self.values[variable] = {}
            self.per_interval[variable] = {}

    def _add_dict(self, x):
        if isinstance(x, dict):
            return x
        this_dict = {}
        if isinstance(x, (list, tuple)):
            if len(x) != len(self.variables):
                raise ValueError(f"lengths must agree: {len(x)} != {len(self.variables)}")
            for a, b in zip(self.variables, x):
                this_dict[a] = b
            return this_dict
        for a in self.variables:
            this_dict[a] = x
        return this_dict

    def add(self, date, val):
        """
        Add data to the interval tracker.

        This populates the self.values and self.per_interval dictionaries.

        Parameters
        ----------
        date : datetime or list/tuple of datetimes (in same variable order/number) or dict of variable/datetime
               if just a datetime, it will associate all vals with that datetime
        val : value or list/tuple of values (in same variable order/number) or dict of variable/values
              if just a value, it assumes only one variable was passed
        """
        these_values = {}  # dict keyed on 'variable' with value ['date', variable_value]
        dates2add = self._add_dict(date)
        vals2add = self._add_dict(val)
        for variable in vals2add:
            these_values[variable] = [dates2add[variable], vals2add[variable]]

        for variable, [vdate, vval] in these_values.items():
            if self.interval == 'year':
                mark = datetime(year=vdate.year, month=12, day=31)
            elif self.interval == 'month':
                mark = get_end_of_month(vdate)
            elif self.interval == 'day':
                mark = datetime(year=vdate.year, month=vdate.month, day=vdate.day)
            elif self.interval == 'hour':
                mark = datetime(year=vdate.year, month=vdate.month, day=vdate.day, hour=vdate.hour)
            elif self.interval == 'minute':
                mark = datetime(year=vdate.year, month=vdate.month, day=vdate.day, hour=vdate.hour, minute=vdate.minute)
            try:
                fval = float(vval)
                self.values[variable].setdefault(mark, 0.0)
                self.values[variable][mark] += fval
            except ValueError:
                if mark not in self.values[variable]:
                    self.values[variable][mark] = vval
                else:
                    previous_late = sorted(self.per_interval[variable][mark])[-1]
                    if vdate > previous_late:
                        self.values[variable][mark] = vval
            self.per_interval[variable].setdefault(mark, [])
            self.per_interval[variable][mark].append(vdate)

    def make(self):
        """
        Convert self.values to time sorted class attribute lists:
            self.<variable_name>
            self.date.<variable_name>
        """
        self.date = Namespace()
        for variable in self.variables:
            setattr(self, variable, [])
            setattr(self.date, variable, [])
            for mark_date in sorted(self.values[variable]):
                getattr(self.date, variable).append(mark_date)
                getattr(self, variable).append(self.values[variable][mark_date])

    def number_date(self):
        """
        Tries to make a sensible float from the time data as a class attribute list:
            self.<interval>.<variable_name>
        """
        setattr(self, self.interval, Namespace())
        if self.interval == 'year':
            for variable in self.variables:
                setattr(self.year, variable, [dt.year for dt in getattr(self.date, variable)])
        elif self.interval == 'month':
            for variable in self.variables:
                setattr(self.month, variable, [dt.year + dt.month / 12.0 for dt in getattr(self.date, variable)])
        else:
            mult = {'day': 1.0, 'hour': 24.0, 'minute': 24.0*60.0}
            for variable in self.variables:
                setattr(getattr(self, self.interval), variable, [mult[self.interval] * (x - getattr(self.date, variable)[0]).days for x in getattr(self.date, variable)])