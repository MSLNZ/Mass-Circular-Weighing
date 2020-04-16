import serial

from .mettler import MettlerToledo
from .mdebalance import Balance
from ..log import log

from ..gui.allocator_thread import AllocatorThread
allocator = AllocatorThread()


class AWBal(Balance):  # TODO: change back to MettlerToledo when connecting to balance
    def __init__(self, record, reset=False, ):
        """Initialise Mettler Toledo Balance, with automatic weight loading, via computer interface

        Parameters
        ----------
        record : equipment record object
            get via Application(config).equipment[alias]
            Requires an MSL.equipment config.xml file
        reset : bool
            True if reset balance desired
        """
        super().__init__(record)

        address = record.user_defined['address']
        self.arduino = None
        '''Return when using arduino:
        serial.Serial(port=address, baudrate=115200)
        self.init_arduino()
        '''

        self.num_pos = record.user_defined['pos']  # num_pos is the total number of available loading positions
        self._positions = None

        self.move_time = 0

    @property
    def mode(self):
        return 'aw'

    @property
    def positions(self):
        """Returns a list of positions for the weight groups in the order the groups appear in the scheme entry."""
        return self._positions

    def init_arduino(self):
        """Initialisation procedure for weight changer arduino - TODO

        Returns
        -------
        Bool to indicate ready status of weight changer
        """
        print(self.arduino.readline().decode())
        # if status BAD, set self._want_abort = True (see parent Balance class)

    def allocate_positions(self, wtgrps, ):
        if len(wtgrps) > self.num_pos:
            log.error('Too many weight groups for balance')
            return None
        allocator.show(self.num_pos, wtgrps)
        self._positions = allocator.wait_for_prompt_reply()
        # TODO: at this point it would be sensible to ask operator to confirm ready for timed move routine to commence
        # e.g. prompt ok_cancel to begin balance initialisation, commence time_max_move
        return self.positions

    def time_max_move(self):
        if not self.want_abort:
            hi = max(self.positions)
            lo = min(self.positions)
            print(hi, lo)
            # self.move_to_pos(hi)
            # start timer
            # self.move_to_pos(lo)
            # stop timer
            # self.move_time = elapsed_time

    def move_to_pos(self, pos):
        if not self.want_abort:
            move_str = 'M '+str(pos)+'\n'   # send: move = M, and position = int
            print(move_str)
            # arduino.write(move_str.encode())
            # reply = arduino.readline().decode()
            # print(reply)

    def load_bal(self, mass, pos):
        """Prompts arduino to move to position and load pan with specified mass"""
        # print(type(mass), type(pos))
        if not self.want_abort:
            # start clock
            self.move_to_pos(pos)

            # wait until move time is up

            load_str = 'L '+str(pos)+'\n'   # send: load = L, and position = int
            print(load_str)
            # arduino.write(loadstr.encode())
            # reply = arduino.readline()

            loaded = True
            if not loaded:
                self._want_abort = True

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

