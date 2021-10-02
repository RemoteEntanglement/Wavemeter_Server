""" Created on Sat Oct  2 17:00:00 2021
    @author: Lee Jeong Hoon
    e-mail: dalsan2113@snu.ac.kr
    
    Module that controls the wavemeter operations.
    It simply fetches the work in the worklist and execute the corresponding
    jobs including updating the channel information, and reply them to the
    clients if needed.
    PIDLoop class runs in another thread concurrently, as it continuously 
    iterate over the channel list to measure the data, update them, and do
    PID if it is enabled.
"""

import time

from PyQt5.QtCore import *

from constant import *
from wavemeter import *
import server_network

class WavemeterController():
    def __init__(self):
        # deprecated - self.server_socket = server_network.ServerSocket(self)
        self.wavemeter = Wavemeter()
        self._server_status = SERVER_STATUS["disconnected"]
        self._work_list = []
        self._channel_list_prio_low =  {}
        self._channel_list_prio_high = {}

        self._mutex = QMutex()
        self._cond = QWaitCondition()

    def _inform_clients(self, message, client_list):
        if type(client_list) != list:
            client_list = [client_list]

        for client in client_list:
            client.toMessageList(message)

    def _broadcast_clients(self, message):
        # todo - broadcast message to all users connected to the server
        pass

    def _start_program(self, initial_channel_list):
        if self._server_status == SERVER_STATUS["started"] \
        or self._server_status == SERVER_STATUS["focused"]:
            # todo - notify the user that the program is already started with STA message
            pass

        self.wavemeter.start_program()
        self._server_status = SERVER_STATUS["started"]

    def _stop_program(self):
        if self._server_status == SERVER_STATUS["stoped"]:
            # todo - notify the user that the program is already stopped with STA message
            pass
        
        self.wavemeter.stop_program()
        self._server_status = SERVER_STATUS["stopped"]

    def _kill_program(self):
        # todo 
        pass

    def _add_user_to_channel(self):
        # todo 
        pass

    def _remove_user_from_channel(self):
        # todo 
        pass

    def _pid_on(self, channel_name, requester):
        ### Check that the channel_name is valid for pid on
        if channel_name not in self.channel_list_low_prio.keys():
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return

        channel = self.channel_list_low_prio[channel_name]
        channel.pid_on = True

        data = []
        data.append(channel_name)
        data.append(channel.target_frequency)
        data.append(channel.pp)
        data.append(channel.ii)
        data.append(channel.dd)
        data.append(channel.gain)
        message = ['C', 'PON', data]

        # deprecated - self.server_socket.send_message_to_specific_clients(message, channel.monitor_list)
        self._inform_clients(message, channel.monitor_list)

    def _pid_off(self, channel_name, requester):
        ### Check that the channel_name is valid for pid off
        if channel_name not in self.channel_list_low_prio.keys():
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return

        channel = self.channel_list_low_prio[channel_name]
        channel.pid_on = False

        message = ['C', 'POF', [channel_name]]
        # deprecated - self.server_socket.send_message_to_specific_clients(message, channel.monitor_list)
        self._inform_clients(message, channel.monitor_list)

    def _focus_on(self, channel_name, requester):
        ### Check that the channel_name is valid for focus on
        if channel_name not in self._channel_list_prio_low.keys():
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return
        elif not self.channel_list_high_prio:
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return
        
        channel = self.channel_list_low_prio[channel_name]
        self.channel_list_high_prio[channel_name] = channel
        self._server_status = SERVER_STATUS["focused"]

        message = ['C', 'FON', [channel_name]]
        self._broadcast_clients(message)

    def _focus_off(self, channel_name, requester):
        ### Check that the channel_name is valid for focus off
        if channel_name not in self._channel_list_prio_low.keys():
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return
        elif channel_name not in self._channel_list_prio_high.keys():
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return

        channel = self.channel_list_low_prio[channel_name]
        self.channel_list_high_prio = {}
        self._server_status = SERVER_STATUS["started"]

        message = ['C', 'FOF', [channel_name]]
        # deprecated - self.server_socket.broadcast_message(message)
        self._broadcast_clients(message)

    def _auto_exposure_on(self, channel_name, requester):
        ### Check that the channel_name is valid for auto exposure on
        if channel_name not in self._channel_list_prio_low.keys():
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return

        channel = self.channel_list_low_prio[channel_name]
        channel.auto_exposure_on = True

        message = ['C', 'AEN', [channel_name]]
        # deprecated - self.server_socket.send_message_to_specific_clients(message, channel.monitor_list)
        self._inform_clients(message, channel.monitor_list)

    def _auto_exposure_off(self, channel_name, requester):
        ### Check that the channel_name is valid for auto exposure off
        if channel_name not in self._channel_list_prio_low.keys():
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return

        channel = self.channel_list_low_prio[channel_name]
        channel.auto_exposure_on = False

        message = ['C', 'AEF', [channel_name]]
        # deprecated - self.server_socket.send_message_to_specific_clients(message, channel.monitor_list)
        self._inform_clients(message, channel.monitor_list)

    def _reply_current_status(self, requester):
        # todo - reply the current wavemeter status back to the requester
        # channel name, users per each channel, fiber, switch, DAC Channel, PID on/off (target freq if on)
        # focus on/off, exp time, pid vals
        pass

    def _update_target_frequency(self, channel_name, target_frequency):
        if channel_name not in self.channel_list_low_prio.keys():
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return

        channel = self.channel_list_low_prio[channel_name]
        channel.target_frequency = target_frequency

        message = ['D', 'TFR', [channel_name, target_frequency]]
        # depreacted - self.server_socket.send_message_to_specific_clients(message, channel.monitor_list)
        self._inform_clients(message, channel.monitor_list)

    def _update_exposure_time(self, channel_name, exposure_time):
        if channel_name not in self.channel_list_low_prio.keys():
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return
        
        channel = self.channel_list_low_prio[channel_name]
        channel.exposure_time = exposure_time

        message = ['D', 'EXP', [channel_name, exposure_time]]
        # deprecated - self.server_socket.send_message_to_specific_clients(message, channel.monitor_list)
        self._inform_clients(message, channel.monitor_list)

    def _update_output_voltage(self, channel_name, output_voltage, user_name):
        if channel_name not in self.channel_list_low_prio.keys():
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return
        
        channel = self.channel_list_low_prio[channel_name]
        # todo - command ArtyS7 to make specified output voltage

        message = ['D', 'VLT', [channel_name, output_voltage]]
        # deprecated - self.server_socket.send_message_to_specific_clients(message, channel.monitor_list)
        self._inform_clients(message, channel.monitor_list)

    def _update_p_value(self, channel_name, p_value, user_name):
        if channel_name not in self.channel_list_low_prio.keys():
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return
        
        channel = self.channel_list_low_prio[channel_name]
        channel.pp = p_value

        message = ['D', 'PPP', [channel_name, p_value]]
        # deprecated - self.server_socket.send_message_to_specific_clients(message, channel.monitor_list)
        self._inform_clients(message, channel.monitor_list)

    def _update_i_value(self, channel_name, i_value, user_name):
        if channel_name not in self.channel_list_low_prio.keys():
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return
        
        channel = self.channel_list_low_prio[channel_name]
        channel.ii = i_value

        message = ['D', 'III', [channel_name, i_value]]
        # deprecated - self.server_socket.send_message_to_specific_clients(message, channel.monitor_list)
        self._inform_clients(message, channel.monitor_list)

    def _update_d_value(self, channel_name, d_value, user_name):
        if channel_name not in self.channel_list_low_prio.keys():
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return
        
        channel = self.channel_list_low_prio[channel_name]
        channel.dd = d_value

        message = ['D', 'DDD', [channel_name, d_value]]
        # deprecated - self.server_socket.send_message_to_specific_clients(message, channel.monitor_list)
        self._inform_clients(message, channel.monitor_list)

    def _update_gain_value(self, channel_name, gain, user_name):
        if channel_name not in self.channel_list_low_prio.keys():
            # todoo - self.server_socket.send_message_to_specific_clients(NAK, [user_name])
            return
        
        channel = self.channel_list_low_prio[channel_name]
        channel.gain = gain

        message = ['D', 'GAN', [channel_name, gain]]
        # deprecated - self.server_socket.send_message_to_specific_clients(message, channel.monitor_list)
        self._inform_clients(message, channel.monitor_list)

    def _capture_current_configuration(self, file_name):
        # todo 
        pass

    # ref - toWorkList(self, cmd): in the DummyDAC
    # cmd = [control, command, data, self] -> self : MessageHandler (or commHandler which I used)
    def toWorkList(self, message):
        """ Translates message to execute the proper functions.
            The argumnet cmd should be the list of four elements, which are control
            character, command string, related data, and client object respectively.

            message : [ control - character | command - string | data - list | MessageHandler ]

            Possible control characters, command strings, and detailed explanation
            about each of them are in the manual.

            As the message comes from the network, this function sends NAK message
            rather than return negative values for the unexpected messages.
        """
        try:
            control = message[0]
            command = message[1]
            data = message[2]
            client = message[3]
        except:
            # todoo - send NAK for invalid message
            pass

        self._work_list.append(message)
        if not self.isRunning():
            self.start()
        if self._thread_status == THREAD_STATUS["standby"]:
            self._cond.wakeAll()

    def run(self):
        while True:
            self._mutex.lock()
            while len(self._work_list):
                self._thread_status = THREAD_STATUS["running"]

                work = self._work_list.pop(0)
                control = work[0]
                command = work[1]
                data = work[2]
                client = work[3]

                if control == 'C':
                    if command == 'SRT':
                        ### data : [0] (list)list of initial channels
                        self._start_program(data[0])
                    elif command == 'STP':
                        ### no data (empty list)
                        self._stop_program()
                    elif command == 'KIL':
                        ### no data (empty list)
                        self._kill_program()
                    elif command == 'UON':
                        ### data : [0] (str)channel name
                        # todo - add_user_to_channel for the channel specified by data[0]
                        pass
                    elif command == 'UOF':
                        ### data : [0] (str)channel name
                        # todo - remove_user_from_channel for the channel specified by data[0]
                        pass
                    elif command == 'PON':
                        ### data : [0] (str)channel name
                        self._pid_on(data[0], client)
                    elif command == 'POF':
                        ### data : [0] (str)channel name
                        self._pid_off(data[0], client)
                    elif command == 'FON':
                        ### data : [0] (str)channel name
                        self._focus_on(data[0], client)
                    elif command == 'FOF':
                        ### data : [0] (str)channel name
                        self._focus_off(data[0], client)
                    elif command == 'AEN':
                        ### data : [0] (str)channel name
                        self._auto_exposure_on(data[0], client)
                    elif command == 'AEF':
                        ### data : [0] (str)channel name
                        self._auto_exposure_off(data[0], client)
                    elif command == 'WMS':
                        ### no data (empty list)
                        self._reply_current_status(client)
                    elif command == 'SCF':
                        ### data : [0] (str)file name
                        self._capture_current_configuration(data[0])
                    elif command == 'CAL':
                        # todoo
                        pass
                    elif command == 'ACL':
                        # todoo
                        pass
                    elif command == 'NAK':
                        # todoo - NAK for invalid message
                        pass
                elif control == 'D':
                    if command == 'TWL':
                        ### data : [0] (str)channel name / [1] (float)target wavelength
                        frequency = unit_convert(data[1])
                        self._update_target_frequency(data[0], frequency)
                    elif command == 'TFR':
                        ### data : [0] (str)channel name / [1] (float)target frequency
                        self._update_target_frequency(data[0], data[1])
                    elif command == 'EXP':
                        ### data : [0] (str)channel name / [1] (int)exposure time
                        self._update_exposure_time(data[0], data[1])
                    elif command == 'VLT':
                        ### data : [0] (str)channel name / [1] (float)voltage
                        self._update_output_voltage(data[0], data[1])
                    elif command == 'PPP':
                        ### data : [0] (str)channel name / [1] (int)P gain
                        self._update_p_value(data[0], data[1])
                    elif command == 'III':
                        ### data : [0] (str)channel name / [1] (int)I gain
                        self._update_i_value(data[0], data[1])
                    elif command == 'DDD':
                        ### data : [0] (str)channel name / [1] (int)D gain
                        self._update_d_value(data[0], data[1])
                    elif command == 'GAN':
                        ### data : [0] (str)channel name / [1] (int)gain
                        self._update_gain_value(data[0], data[1])
                    else:
                        # todoo - send NAK for invalid message
                        pass
                else:
                    # todoo - send NAK for invalid message
                    pass

            self._thread_status = THREAD_STATUS["standby"]
            self._cond.wait(self._mutex)
            self._mutex.unlock()

class PIDLoop(QObject):
    signal_toggle_loop = pyqtSignal()
    signal_new_measured_data = pyqtSignal(list)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.is_running = False
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()

    def toggle_loop(self):
        self.is_running = not self.is_running
        if self.is_running:
            # todo - wm.Operation(wm.cCtrlStartMeasurement)
            self.wait_condition.wakeAll()
        else:
            # todo - wm.Operation(wm.cCtrlStopAll)
            pass

    def run(self):
        last_time = time.time()
        while True:
            time_consumed = 0
            self.mutex.lock()
            if self.is_running:
                # todo 
                pass
            else:
                self.wait_condition.wait(self.mutex)
            if time_consumed < 1000 :# and not self.controller.focused:
                time.sleep(1 - 0.001 * time_consumed)
            self.mutex.unlock()

class Channel():
    def __init__(self, name, exposure_time, pid, fiber_switch,
            DAC_channel):
        ### pid : list of [0]P, [1]I, [2]D, [3]gain
        self.name = name
        self.monitor_list = []
        self.fiber_switch = fiber_switch
        self.DAC_channel = DAC_channel

        self.current_frequency = float(0.0)
        self.weighted_frequency = float(0.0)
        self.target_frequency = float(0.0)
        self.current_output_voltage = float(0.0)
        self.recent_output_voltage = float(0.0)
        
        self.exposure_time = exposure_time
        self.pp = pid[0]
        self.ii = pid[1]
        self.dd = pid[2]
        self.gain = pid[3]
        self.differentiator = float(0.0)
        self.proportional = float(0.0)
        self.accumulator = float(0.0)
        self.current_time = time.time()

        self.auto_exposure_on = False
        self.pid_on = False

def unit_convert(value):
    """ Return unit converted postive value if unit conversion is successful.
        Return the original value, otherwise.
        
        Convert frequency to wavelength, wavelength to frequency.
    """
    SPEED_OF_LIGHT = 299792458.0
    if value > 0:
        return SPEED_OF_LIGHT/value
    else:
        return value
