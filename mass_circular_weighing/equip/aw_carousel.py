'''Class for Mettler Toledo Balance with computer interface and carousel weight changer'''
from time import perf_counter

from msl.equipment import MSLTimeoutError
from msl.qt import prompt, application

from ..log import log
from .mettler import MettlerToledo

from ..gui.threads.allocator_thread import AllocatorThread
allocator = AllocatorThread()


class AWBalCarousel(MettlerToledo):
    def __init__(self, record, reset=False, ):
        """Initialise Mettler Toledo Balance,
        with automatic weight loading in carousel configuration,
        via computer interface.

        Parameters
        ----------
        record : equipment record object
            get via Application(config).equipment[alias]
            Requires an MSL.equipment config.xml file
        reset : bool
            True if reset balance desired
        """
        super().__init__(record)

        self.num_pos = record.user_defined['pos']  # num_pos is the total number of available loading positions
        self._positions = None

        self.move_time = 0

    @property
    def mode(self):
        return 'aw_c'

    @property
    def positions(self):
        """Returns a list of positions for the weight groups in the order the groups appear in the scheme entry."""
        return self._positions

    def allocate_positions(self, wtgrps, ):
        """

        Parameters
        ----------
        wtgrps

        Returns
        -------

        """
        if len(wtgrps) > self.num_pos:
            log.error('Too many weight groups for balance')
            return None
        allocator.show(self.num_pos, wtgrps)
        self._positions = allocator.wait_for_prompt_reply()
        if not self.positions:
            self._want_abort = True

        return self.positions

    def move_to(self, pos):
        # takes integer position
        if not self.want_abort:
            # display  "Handler Turning to Position: " + Weight

            reply = self._query("MOVE" + str(pos))
            print(reply)

            if reply == "Some logical string":  # TODO: work out what this string is!
                self.wait_for_ready()

            else:
                self._raise_error(reply)

    def time_move(self):
        if not self.want_abort:
            times = []
            print("Moving to last position")
            self.move_to(self.positions[-1])
            for pos in self.positions:
                print("Moving to position "+pos)
                t0 = perf_counter()
                self.move_to(pos)
                times.append(perf_counter() - t0)

            print(times, max(times))

            self.move_time = max(times) + 5

    def lower_handler(self):
        if not self.want_abort:
            print("SINK")
            # can get handler to display text such as "Sinking position: " + Weight here if desired
            reply = self._query("SINK")
            print(reply)

            if reply == "Some logical string":  # TODO: work out what this string is!
                self.wait_for_ready()

            else:
                self._raise_error(reply)

    def raise_handler(self):
        if not self.want_abort:
            print("LIFT")
            # can get handler to display text such as "Sinking position: " + Weight here if desired
            reply = self._query("LIFT")
            print(reply)

            if reply == "Some logical string":  # TODO: work out what this string is!
                self.wait_for_ready()

            else:
                self._raise_error(reply)

    def load_bal(self, mass, pos):
        while not self.want_abort:
            t0 = perf_counter()
            self.move_to(pos)
            t1 = perf_counter()

            # wait for some time to make all moves same - want a sleep_until function which allows other events to occur
            app = application()
            time = perf_counter() - t0 # or t1?
            while time < self.stable_wait:  # for AX1006, stable wait is 35 s
                app.processEvents()

            # 'brake time' = 35 s

    def unload_bal(self, mass, pos):
        """Prompts arduino to unload specified mass from pan"""
        if not self.want_abort:
            # send command to arduino to unload balance
            unload_str = 'U '+str(pos)+'\n'
            # self.arduino.write(unload_str.encode())  # send: unload = U, and position = int
            # reply = self.arduino.readline().decode()
            # print(reply)
            # winsound.Beep(880, 300)
            print('Unloaded '+mass+' (position '+str(pos)+')')


    #TODO: add clean up to close connection




    def wait_for_ready(self):
        app = application()
        t0 = perf_counter()

        while True:  # wait for handler to finish task
            app.processEvents()
            try:
                r = self.connection.read().split()
                print(r)
                if "ready" in r:
                    return True
                elif r:
                    print(r)
            except MSLTimeoutError:
                if perf_counter() - t0 > self.intcaltimeout:
                    raise TimeoutError("Task took longer than expected")
                else:
                    print('Waiting for task to complete')
                    log.info('Waiting for task to complete')

