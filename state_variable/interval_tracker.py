from datetime import datetime, timedelta
from copy import copy
from argparse import Namespace


def get_end_of_month(date):
    nm = datetime(year=date.year, month=date.month, day=1) + timedelta(days=32)
    return datetime(year=nm.year, month=nm.month, day=1) - timedelta(days=1)


class IntervalTracker:
    """
    Group time-based data by Interval (year, month, day, hour, minute, second).

    If values are numeric, it will sum.  If not, will keep latest.
    """
    def __init__(self, interval, variables='value'):
        self.interval = interval.lower()
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

    def add(self, date, val):
        """
        Add to the interval tracker.  Probably overall comprehensive and flexible...

        Parameters
        ----------
        date : datetime or list/tuple of datetimes (in same variable order/number) or dict of variable/datetime
               if just a datetime, it will associate all vals with that datetime
        val : value or list/tuple of values (in same variable order/number) or dict of variable/values
              if just a value, it assumes only one variable was passed and date must agree
        """
        these_values = {}  # dict keyed on variable with value [date, variable_value]

        if not isinstance(val, (list, tuple, dict)) and not isinstance(date, (list, tuple, dict)):
            if len(self.variables) == 1:
                these_values[self.variables[0]] = [date, val]
            else:
                raise ValueError("Date/val values must have only one class variable.")
        elif isinstance(val, dict):
            if isinstance(date, dict):
                if len(val) == len(date):
                    for kvar, kval in val.items():
                        these_values[kvar] = [date[kvar], kval]
                else:
                    raise ValueError("Specified date and val dicts must match.")
            elif isinstance(date, (list, tuple)):
                raise ValueError("Must be bare datetime if val is dict and date is not.")
            else:
                for kvar, kval in val.items():
                    these_values[kvar] = [date, kval]
        elif isinstance(val, (list, tuple)):
            if len(val) != len(self.variables):
                raise ValueError(f"value and variable lengths must agree: {len(val)} != {len(self.variables)}")
            if isinstance(date, (list, tuple)):
                if len(date) != len(self.variables):
                    raise ValueError(f"date and variable lengths must agree: {len(val)} != {len(self.variables)}")
                else:
                    for xvar, xval, xdt in zip(self.variables, val, date):
                        these_values[xvar] = [xdt, xval]
            elif isinstance(date, dict):
                for xvar, xval in zip(self.variables, val):
                    these_values[xvar] = [date[xvar], xval]
            else:
                for xvar, xval in zip(self.variables, val):
                    these_values[xvar] = [date, xval]

        for variable, [vdate, vval] in these_values.items():
            if self.interval[0] == 'd':
                mark = datetime(year=vdate.year, month=vdate.month, day=vdate.day)
            elif self.interval[0] == 'm':
                mark = get_end_of_month(vdate)
            elif self.interval[0] == 'y' or self.interval[0] == 'a':
                mark = datetime(year=vdate.year, month=12, day=31)
            else:
                raise ValueError(f"Don't do interval {self.interval} yet.")
            self.per_interval[variable].setdefault(mark, [])
            self.per_interval[variable][mark].append(vdate)
            try:
                fval = float(vval)
                self.values[variable].setdefault(mark, 0.0)
                self.values[variable][mark] += fval
            except ValueError:
                if mark not in self.values[variable]:
                    self.values[mark] = (vdate, vval)
                else:
                    previous_date, previous_val = self.values[variable][mark]
                    if self.values[variable][mark][0] > previous_date:
                        self.values[variable][mark] = (vdate, vval)

    def make(self):
        self.date = Namespace()
        for variable in self.variables:
            setattr(self, variable, [])
            setattr(self.date, variable, [])
            for mark_date in sorted(self.values[variable]):
                getattr(self.date, variable).append(mark_date)
                getattr(self, variable).append(self.values[variable][mark_date])


    def number_date(self):
        if self.interval[0] == 'y' or self.interval[0] == 'a':
            self.year = Namespace()
            for variable in self.variables:
                setattr(self.year, variable, [dt.year for dt in getattr(self.date, variable)])
        elif self.interval[0] == 'm':
            self.month = Namespace()
            for variable in self.variables:
                setattr(self.year, variable, [dt.year + dt.month / 12.0 for dt in getattr(self.date, variable)])
        else:
            print("Only do yearly for now.")