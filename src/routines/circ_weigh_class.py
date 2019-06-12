

class CircWeigh(object):
    def __init__(self, scheme_entry):
        """Initialises a circular weighing for a single weighing in the scheme

        Parameters
        ----------
        scheme_entry : str
            the masses to be weighed in order of weighing, separated by white space e.g. "1a 1b 1c 1d"
        """
        self._sequences = {2: 5, 3: 4, 4: 3, 5: 3}  # key: number of items in weighing, value: number of cycles
        self.masses = scheme_entry.split()
        self.num_masses = len(self.masses)
        self.positiondict = {}
        for i in range(self.num_masses):
            self.positiondict[i] = self.masses[i]
        self.num_cycles = (self._sequences[self.num_masses])





