"""
An independent thread that does a circular weighing.
At present, the thread allows for three options of run mode - may want to simplify by removing auto mode?
"""
import threading
import time
import numpy as np
import csv

class Thread(threading.Thread):  # TODO: why is this thread called Thread?
    def __init__(self,masses,mass_positions,reads_per_mass,centerings,parent,run_option,num_cycles):
        threading.Thread.__init__(self)

        # TODO: need to import connection to balance (which actually determines run_option)
        self.masses = masses
        self.mass_positions = mass_positions
        self.reads_per_mass = reads_per_mass
        self.centerings = centerings
        self.parent = parent
        self.num_cycles = num_cycles
        self.run_option = run_option  # see note re balance
        self.first_read_time = None #Time of first reading
        self._want_abort = False
        self.space_pressed = False
        self.start()
        
    def run(self):  # TODO: add MANUAL as run option and make sure this method is consistent
        """Perform a circular weighing with either:
            automatic weight loading and data collection (AUTO or aw),
            manual weight loading with automatic data collection (SEMI or mw), or
            manual weight loading and data entry (mde)"""
        if self.run_option == 'AUTO':
            self.auto()
        elif self.run_option == 'SEMI':
            self.semi_auto()
        else:
            print("Valid run options are AUTO or SEMI")
            
    def write_to_popup(self,s):
        """Call the parent.update_popup method if a parent exists"""
        if not self._want_abort:
            if self.parent:
                self.parent.update_popup(s)
            else:
                print(s)
            
    def semi_auto(self):  # TODO: add check that T, RH ok to start mmt cycle
        """Data gathering for semi-auto option"""
        self.report_event("Semi auto measurement")
        self.reset_instrument_semi()
        result_rows = []
        for reading in range(self.reads_per_mass):
            row = []
            for mass in self.masses:
                if not self._want_abort:
                    s = "Set mass:\n"+str(mass) #Some string for printing.
                    self.write_to_popup(s) #send it to the pop-up window.
                    self.report_event("Reading {} for mass {}".format(reading,mass))
                    self.wait_for_space()  # waits for user to load mass
                    s = "Measuring:\n"+mass #Update the pop-up title.
                    self.write_to_popup(s)
                    weight_reading = self.read_weight()
                    row.append(self.time_from_first())
                    row.append(weight_reading)
            result_rows.append(row)
        self.write_to_popup("Done")
        self.balance.close()
        self.return_results(result_rows)
    
    def auto(self):
        """Data gathering for automatic options, INCOMPLETE"""
        self.reset_instrument_auto()
        self.do_centerings()
        result_rows = []
        for cycle in range(self.num_cycles):
            for reading in range(self.reads_per_mass):
                row = []
                string = "Measuring"
                for pos,mass in zip(self.mass_positions,self.masses):
                    if not self._want_abort:
                        self.report_event("Reading number {} for mass {}".format(reading,mass))
                        string +="."
                        self.write_to_popup(string)
                        self.position(pos)
                        weight_reading = self.read_weight()
                        row.append(self.time_from_first())
                        row.append(weight_reading)
                result_rows.append(row)
        self.write_to_popup("Done")
        self.balance.close()
        self.return_results(result_rows)
        
    def do_centerings(self):
        """A simple copy of the above readings, but only positions masses and thats it."""
        for c in range(self.centerings):
            string = "Centering"
            for pos,mass in zip(self.mass_positions,self.masses):
                if not self._want_abort:
                    self.report_event("Centering number {} for mass {}".format(c,mass))
                    string +="."
                    self.write_to_popup(string)
                    self.position(pos)
                    
    def time_from_first(self):
        """Saves the time of the first reading, then calculates
        the time with that as reference. returns time in minutes for no reason"""
        if self.first_read_time == None:
            self.first_read_time = time.time()
            t_in_s = 0.0
        else:
            t_in_s = float(time.time()-self.first_read_time)
        return t_in_s/60.0
    
    def reset_instrument_auto(self):
        """Just a sub function to reset the instrument, for the automatic case"""
        self.balance.write("@")
        self.balance.write("LIFT")
        self.wait(2)
        self.balance.write("Z")
        
    def reset_instrument_semi(self):
        """Reset the instrument for the semi auto case, maybe unecessary"""
        self.balance.write("@")
        for i in range(3):
            string = None
            try:
                string = self.balance.read()
            except self.visa.VisaIOError:
                pass
            if string == 'I4 A "B525073136"':
                break
    
    def return_results(self,data):
        """Once data is collected into a table format, cal the parent.recieve_results method if one exists.
        If no parent exists, save the data as csv with mass names and time stamp."""
        if not self._want_abort:
            if self.parent == None:
                name = time.strftime("%Y.%m.%d.%H.%M.%S",time.localtime()) #Time stamp
                for mass in self.masses:
                    name += "_"+str(mass) #appends the masses involved.
                name += ".csv" #csv file type.
                with open(name,'wb') as f:
                    writer = csv.writer(f, delimiter=',')
                    writer.writerow(["Circular algorithm data and results"])
                    writer.writerow(["Mass positions:"]+self.mass_positions)
                    titles = [] #Create the mass name titles seperated by empty spaces.
                    for name in self.masses:
                        titles = titles + ['',name]
                    writer.writerow(titles)
                    writer.writerows(data)
            else:
                self.parent.recieve_results(data,self.mass_positions)
                
    def report_event(self,text):
        """Report some text, calls parent.report_event. This prints to the parent event report box."""
        #Perhaps save a log file idk.
        if self.parent:
            self.parent.report_event(text)
        else:
            print(text)
        
    def position(self,pos):
        """A sub routine to positions masses, incomplete. Used by the auto measuring thing"""
        self.lift()
        self.report_event("Moving to "+str(pos))
        self.lift_sink_move("MOVE"+str(pos))
        self.sink(0) #Setting of zero wait time following the first sink.
        self.sink()
        
    def lift(self):
        self.report_event("Lifting")
        self.lift_sink_move("LIFT")
        
    def sink(self,wait=35):
        """Default of 35 second wait, but for first wait will set 0"""
        self.report_event("Sinking")
        self.lift_sink_move("SINK")
        self.wait(wait)
        
    def lift_sink_move(self,word):
        """Lift sink or move once and check for ready state from balance.
        If it takes too long just abort"""
        #done_readings = ['ready\r\n','ERROR: In weighing position already.ready\r\n','ERROR: In top position already. Z -\r\n']
        
        start_time = time.time()
        self.balance.write(word)
        done = False
        while not done:
            if self._want_abort:
                break
            try:
                r = self.balance.read()
                self.report_event(repr(r))
            except self.visa.VisaIOError:
                r=''
                
            if not self.simulated:
                if 'ready' in r: #See "done_readings", I think 'ready' only appears when the balance is happy. This might need to be changed.
                    done = True
                    self.report_event("Balance in position")
                    
                elif time.time()-start_time > 120:
                    self.report_event("Waited too long, moving on.")
                    done = True
            else:
                self.report_event("Simulated, not waiting for 'ready'")
                done = True
        
                
    def read_weight(self):
        """A function to read the weight of the balance once it is stable"""
        if self.run_option == 'SEMI': #In the case of semi auto readings we need to wait for stability.
            self.wait_for_stable()

        readings = []
        self.balance.write("SI") #SI = Send immediatly
        for i in range(3):
            reading = self.float_reading()  # TODO: use balance method directly?
            readings.append(reading)
        avg = np.average(readings)
        self.report_event("Average reading:")
        self.report_event(avg)
        return avg
    
    def wait_for_stable(self):  # TODO: could include stable criteria in get_mass()?  also seems overly complicated!
        self.balance.write("S")
        stable = False
        while stable == False:
            if self._want_abort:
                break
            try:
                #Tries to read and also turn reading into a float.
                #Replaces all letters in the number similarly to float_reading,
                #except does not replace the "D", so if the reading is dynamic it
                #will run into an exception.
                #An easier test is "if 'D' in reading:" but this wont be unique to
                #weight readings, maybe the balance can return other strings with 'D' in them.
                val = self.balance.read().replace(' ','')
                val = val.replace('S','')
                val = val.replace('kg','e3')
                val = val.replace('mg','e-3')
                val = val.replace('g','')
                discarded = float(val)
                #so fails if wait is not stable
                #And continues to here if it sucesfully turned the reading to a float.
                stable = True
            except ValueError: #There is nothing to do except go and try again.
                pass#self.wait(0.1)
            
    def float_reading(self):
        """Reads the balance, and removes spaces and letters from the reading preparing it to be cast into a float"""
        #TODO: use get_mass() from balance class
    
    def abort(self):
        """The abort of the thread, flags it as aborted"""
        self.write_to_popup("Aborted")
        self._want_abort = True
        
    def wait_for_space(self):  # TODO: could be part of 'load balance' method in balance class?
        """Waits until space key is hit, checks the abort flag."""
        #Waits for space key to be pressed in main table
        self.space_pressed = False
        if self.parent:
            if not self._want_abort:
                self.report_event("Waiting for [space] key press")
            while not self.space_pressed:
                if self._want_abort:
                    break
        else:
            self.report_event("Press enter to continue")
            while True: #loops for ever
                a = raw_input()
                if a == '':
                    break
                if self._want_abort:
                    break
            
    def wait(self, period):
        """Waits a desired period of time, checking the abort flag."""
        initial = time.time()
        if self.simulated:
            return
        if self._want_abort == False:
            self.report_event("Waiting for {}s".format(period))
            while time.time()-initial < period:
                if self._want_abort:
                    period = 0
    
if __name__ == "__main__":
    #sample setup here, for running tests or running this without a parent.
    #perhaps it can save the reading results to csv is no parent is present, that way
    #it is possible to run the whole thing without the gui.
    port = 'ASRL2::INSTR'
    masses = ['100A','100']
    mass_positions = [1,2]
    reads_per_mass = max(7-len(mass_positions),3)
    run_option = 'SEMI'#'AUTO'
    centerings = 1
    num_cycles = 1
    parent = None
    a = Thread(port,masses,mass_positions,reads_per_mass,centerings,parent,run_option,num_cycles,simulated=False)
    
