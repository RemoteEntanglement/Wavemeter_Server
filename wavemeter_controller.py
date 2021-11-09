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
import socket
import os
from configparser import ConfigParser

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from constant import *
from wavemeter import *

_file_name = os.path.realpath(__file__)
_home_dir = os.path.dirname(_file_name)

class WavemeterController(QThread):
    def __init__(self):
        """ Initialize internal data structures
            1. _server_status : Can have three values - stopped, started, and focused.
            2. _work_list : List of message that should be handled. Messages include the
              request to update the settings, save configurations, or reply server info.
            3. _channel_list : Dictionary of current channel lists which are read from
              the config file. It has key-value pair of (channel_name, Channel object).
              Each Channel object has the list of name of monitoring clients internally.
            4. _client_list : Dictionary of currently connected clients. It has key-value
              pair of (client_name, Client object). Each Client object has the list of name
              of monitoring channels internally.
        """
        super().__init__()
        self.wavemeter = Wavemeter()
        self.pid_loop = PIDLoop(self)
        self._server_status = SERVER_STATUS["stopped"]
        self._thread_status = THREAD_STATUS["standby"]
        self._work_list = []
        self._channel_list_prio_low =  {}
        self._channel_list_prio_high = {}
        self._client_list = {}

        self._mutex = QMutex()
        self._cond = QWaitCondition()

        self.pid_loop.start()

        self._open_config()

    def _open_config(self):
        """ Initialize channel list by reading configuration. """
        _file_name = os.path.join(_home_dir, 'config', socket.gethostname() + ".ini")
        if not os.path.isfile(_file_name):
            _file_name = QFileDialog.getOpenFileName(self, 'Wavemeter Configuration File',
            os.path.join(_home_dir, 'config'))[0]

        parser = ConfigParser()
        parser.read(_file_name)

        for section in parser.sections():
            if not section == 'PID' and not section.startswith('CH'):
                # todo - exception
                continue

            if section == 'PID':
                try:
                    self.switch_safe = int(parser[section]['switch safe'])
                    self.auto_exposure_step = float(parser[section]['auto exposure step'])
                    self.max_frequency_offset = float(parser[section]['max freq offset'])
                    self.max_frequency_change = float(parser[section]['max freq change'])
                except:
                    # todo - exception
                    return
            elif section.startswith('CH'):
                try:
                    name = parser[section]['name']
                    fiber_switch = int(parser[section]['fiber switch'])
                    dac_channel = int(parser[section]['dac channel'])
                    target_frequency = float(parser[section]['target frequency'])
                    exposure_time = int(parser[section]['exposure time'])
                    p_value = int(parser[section]['pp'])
                    i_value = int(parser[section]['ii'])
                    d_value = int(parser[section]['dd'])
                    gain = int(parser[section]['gain'])
                except:
                    # todo - exception
                    continue

                self._channel_list_prio_low[name] = Channel(name, exposure_time, \
                    [p_value, i_value, d_value, gain], fiber_switch, dac_channel, target_frequency)

    def _inform_clients(self, message, client_list):
        """ Send message to multiple clients. client_list is a string or a list of
            clients' name.
        """
        if type(client_list) != list:
            client_list = [client_list]

        for client_name in client_list:
            client_handler = self._client_list[client_name]
            client_handler.send_message(message)

    def _broadcast_clients(self, message):
        """ Broadcast message to all clients who are listening the wavemeter """
        for client_handler in self._client_list.values():
            client_handler.send_message(message)

    def _new_connection(self, client_name, client_handler):
        """ For the newly connecting client, enroll it to the client list and 
            reply with the current server status to let the client initialize its
            UI and data structures.
        """
        new_client_obj = Client(client_name, client_handler)
        self._client_list[client_name] = new_client_obj

        message = ['C', 'WVM', 'STA', [self._server_status]]
        client_handler.toMessageList(message)

    def _start_measurement(self, initial_channel_list, requester_handler):
        """ If the program is already started or focused, reply the current status
            to the requester only.
        """
        if self._server_status == SERVER_STATUS["started"] \
        or self._server_status == SERVER_STATUS["focused"]:
            message = ['C', 'WVM', 'STA', [self._server_status]]
            requester_handler.toMessageList(message)
            return

        ### After starting the program, broadcast the change of the status to all users
        self.wavemeter.start_measurement()
        self._server_status = SERVER_STATUS["started"]
        self.pid_loop.activate_loop()
        message = ['C', 'WVM', 'STA', [self._server_status]]
        self._broadcast_clients(message)

    def _stop_measurement(self, requester_handler):
        """ If the program is already stopped, reply the current status to the requester only """
        if self._server_status == SERVER_STATUS["stopped"]:
            message = ['C', 'WVM', 'STA', [self._server_status]]
            requester_handler.toMessageList(message)
            return

        ### After stopping the program, broadcast the change of the status to all users
        self.wavemeter.stop_measurement()
        self._server_status = SERVER_STATUS["stopped"]
        self.pid_loop.inactivate_loop()
        message = ['C', 'WVM', 'STA', [self._server_status]]
        self._broadcast_clients(message)

    def _kill_program(self):
        """ 1) Kill the highfinesse wavemeter program. 2) Disconnect all clients. """
        self.wavemeter.stop_measurement()
        self._server_status = SERVER_STATUS["stopped"]

    def _add_user_to_channel(self, channel_list, requester):
        """ 1) Update monitor list of all channels in channel_list
            2) Update channel_list of client designated by client_name
        """
        client_name = requester.user_name
        client_obj = self._client_list[client_name]

        for channel_name in channel_list:
            if self._server_status == SERVER_STATUS["started"] and \
                channel_name not in self._channel_list_prio_low.keys():
                continue
            elif self._server_status == SERVER_STATUS["focused"] and \
                channel_name not in self._channel_list_prio_high.keys():
                continue
            channel_obj = self._channel_list_prio_low[channel_name]
            channel_obj.add_monitor_client(client_name)
            client_obj.subscribe_channel(channel_name)
        self.pid_loop.activate_loop()

    def _remove_user_from_channel(self, channel_name, requester):
        """ 1) Update monitor list of all channels in channel_list
            2) Update channel_list of client designated by client_name
        """
        client_name = requester.user_name
        try:
            client_obj = self._client_list[client_name]
            channel_obj = self._channel_list_prio_low[channel_name]

            client_obj.unsubscribe_channel(channel_name)
            channel_obj.remove_monitor_client(client_name)
        except (KeyError, ValueError) as err:
            # todo - exception
            pass

    def _pid_on(self, channel_name, requester=None):
        ### Check that the channel_name is valid for pid on
        if channel_name not in self._channel_list_prio_low.keys():
            ### pid on to non-existing channel
            # todo - exception
            return
        elif self._server_status == SERVER_STATUS["focused"] and \
            channel_name not in self._channel_list_prio_high.keys():
            ### pid on while another channel is focused
            # todo - exception
            return

        channel = self._channel_list_prio_low[channel_name]
        channel.pid_on = True

        data = []
        data.append(channel_name)
        data.append(channel.target_frequency)
        data.append(channel.pp)
        data.append(channel.ii)
        data.append(channel.dd)
        data.append(channel.gain)
        message = ['C', 'WVM', 'PON', data]

        self._inform_clients(message, channel.monitor_list)

    def _pid_off(self, channel_name, requester=None):
        ### Check that the channel_name is valid for pid off
        if channel_name not in self._channel_list_prio_low.keys():
            ### pid off to non-existing channel
            # todo - exception
            return
        elif self._server_status == SERVER_STATUS["focused"] and \
            channel_name not in self._channel_list_prio_high.keys():
            ### pid off while another channel is focused
            # todo - exception
            return

        channel = self._channel_list_prio_low[channel_name]
        channel.pid_on = False

        message = ['C', 'WVM', 'POF', [channel_name]]
        self._inform_clients(message, channel.monitor_list)

    def _focus_on(self, channel_name, requester=None):
        ### Check that the channel_name is valid for focus on
        if channel_name not in self._channel_list_prio_low.keys():
            ### focus on to non-existing channel
            # todo - exception
            return
        elif not self._channel_list_prio_high or self._server_status == SERVER_STATUS["focused"]:
            ### focus on while another channel is already focused
            # todo - exception
            return

        channel = self._channel_list_prio_low[channel_name]
        self._channel_list_prio_high[channel_name] = channel
        self._server_status = SERVER_STATUS["focused"]

        message = ['C', 'WVM', 'FON', [channel_name]]
        self._broadcast_clients(message)

    def _focus_off(self, channel_name, requester=None):
        ### Check that the channel_name is valid for focus off
        if channel_name not in self._channel_list_prio_low.keys():
            ### focus off to non-existing channel
            # todo - exception
            return
        elif channel_name not in self._channel_list_prio_high.keys() or \
            self._server_status == SERVER_STATUS["started"]:
            ### focus off to non-focused channel
            # todo - exception
            return

        self._channel_list_prio_high = {}
        self._server_status = SERVER_STATUS["started"]

        message = ['C', 'WVM', 'FOF', [channel_name]]
        self._broadcast_clients(message)

    def _auto_exposure_on(self, channel_name, requester=None):
        ### Check that the channel_name is valid for auto exposure on
        if channel_name not in self._channel_list_prio_low.keys():
            ### auto exposure on to non-existing channel
            # todo - exception
            return
        elif self._server_status == SERVER_STATUS["focused"] and \
            channel_name not in self._channel_list_prio_high.keys():
            ### auto exposure on while another channel is focused
            # todo - exception
            return

        channel = self._channel_list_prio_low[channel_name]
        channel.auto_exposure_on = True

        message = ['C', 'WVM', 'AEN', [channel_name]]
        self._inform_clients(message, channel.monitor_list)

    def _auto_exposure_off(self, channel_name, requester=None):
        ### Check that the channel_name is valid for auto exposure off
        if channel_name not in self._channel_list_prio_low.keys():
            ### auto exposure off to non-existing channel
            # todo - exception
            return
        elif self._server_status == SERVER_STATUS["focused"] and \
            channel_name not in self._channel_list_prio_high.keys():
            ### pid on while another channel is focused
            # todo - exception
            return

        channel = self._channel_list_prio_low[channel_name]
        channel.auto_exposure_on = False

        message = ['C', 'WVM', 'AEF', [channel_name]]
        self._inform_clients(message, channel.monitor_list)

    def _reply_current_status(self, requester):
        # todo - build server status message
        message = ['D', 'WVM', 'WMS', []]
        self._inform_clients(message, requester.username)

    def _update_current_frequency(self, channel_name, current_frequency):
        if channel_name not in self._channel_list_prio_low.keys():
            # todo - exception
            return

        channel = self._channel_list_prio_low[channel_name]
        channel.current_frequency = current_frequency

        message = ['D', 'WVM', 'CFR', [channel_name, current_frequency]]
        self._inform_clients(message, channel.monitor_list)

    def _update_target_frequency(self, channel_name, target_frequency):
        if channel_name not in self._channel_list_prio_low.keys():
            # todo - exception
            return

        channel = self._channel_list_prio_low[channel_name]
        channel.target_frequency = target_frequency

        message = ['D', 'WVM', 'TFR', [channel_name, target_frequency]]
        self._inform_clients(message, channel.monitor_list)

    def _update_exposure_time(self, channel_name, exposure_time):
        if channel_name not in self._channel_list_prio_low.keys():
            # todo - exception
            return
        
        channel = self._channel_list_prio_low[channel_name]
        channel.exposure_time = exposure_time

        message = ['D', 'WVM', 'EXP', [channel_name, exposure_time]]
        self._inform_clients(message, channel.monitor_list)

    def _update_output_voltage(self, channel_name, output_voltage):
        if channel_name not in self._channel_list_prio_low.keys():
            # todo - exception
            return
        
        channel = self._channel_list_prio_low[channel_name]
        # todo - command ArtyS7 to make specified output voltage

        message = ['D', 'WVM', 'VLT', [channel_name, output_voltage]]
        self._inform_clients(message, channel.monitor_list)

    def _update_p_value(self, channel_name, p_value):
        if channel_name not in self._channel_list_prio_low.keys():
            # todo - exception
            return
        
        channel = self._channel_list_prio_low[channel_name]
        channel.pp = p_value

        message = ['D', 'WVM', 'PPP', [channel_name, p_value]]
        self._inform_clients(message, channel.monitor_list)

    def _update_i_value(self, channel_name, i_value):
        if channel_name not in self._channel_list_prio_low.keys():
            # todo - exception
            return
        
        channel = self._channel_list_prio_low[channel_name]
        channel.ii = i_value

        message = ['D', 'WVM', 'III', [channel_name, i_value]]
        self._inform_clients(message, channel.monitor_list)

    def _update_d_value(self, channel_name, d_value):
        if channel_name not in self._channel_list_prio_low.keys():
            # todo - exception
            return
        
        channel = self._channel_list_prio_low[channel_name]
        channel.dd = d_value

        message = ['D', 'WVM', 'DDD', [channel_name, d_value]]
        self._inform_clients(message, channel.monitor_list)

    def _update_gain_value(self, channel_name, gain):
        if channel_name not in self._channel_list_prio_low.keys():
            # todo - exception
            return
        
        channel = self._channel_list_prio_low[channel_name]
        channel.gain = gain

        message = ['D', 'WVM', 'GAN', [channel_name, gain]]
        self._inform_clients(message, channel.monitor_list)

    def _inform_apd_value(self, channel_name, data):
        if channel_name not in self._channel_list_prio_low.keys():
            # todo - exception
            return

        channel = self._channel_list_prio_low[channel_name]
        message = ['D', 'WVM', 'APD', [channel_name, data[0], data[1], data[2]]]
        self._inform_clients(message, channel.monitor_list)

    def _capture_current_configuration(self, file_name=""):
        parser = ConfigParser()

        if file_name == "":
            file_name = socket.gethostname() + ".ini"
        file_path = os.path.join(_home_dir, 'config', file_name)

        channel_index = 1
        parser['PID'] = {
            'switch safe': self.switch_safe,
            'auto exposure step': self.auto_exposure_step,
            'max freq offset': self.max_frequency_offset,
            'max freq change': self.max_frequency_change
        }
        for channel_name, channel_obj in self._channel_list_prio_low.items():
            parser['CH'+str(channel_index)] = {
                'name': channel_name,
                'fiber switch': channel_obj.fiber_switch,
                'dac channel': channel_obj.DAC_channel,
                'target frequency': channel_obj.target_frequency,
                'exposure time': channel_obj.exposure_time,
                'pp': channel_obj.pp,
                'ii': channel_obj.ii,
                'dd': channel_obj.dd,
                'gain': channel_obj.gain
            }
            channel_index += 1

        with open(file_path, 'w+') as config_file:
            parser.write(config_file)

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
            # todo - exception
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
                client_handler = work[3]

                if control == 'C':
                    if command == 'CON':
                        ### data : [0] (str)client name
                        self._new_connection(data[0], client_handler)
                    elif command == 'DCN':
                        # todo
                        pass
                    elif command == 'SRT':
                        ### data : [0] (list)list of initial channels
                        self._start_measurement(data[0], client_handler)
                    elif command == 'STP':
                        ### no data (empty list)
                        self._stop_measurement()
                    elif command == 'KIL':
                        ### no data (empty list)
                        self._kill_program()
                    elif command == 'UON':
                        ### data : [0] (str)channel name
                        self._add_user_to_channel([data[0]], client_handler)
                    elif command == 'UOF':
                        ### data : [0] (str)channel name
                        self._remove_user_from_channel(data[0], client_handler)
                    elif command == 'PON':
                        ### data : [0] (str)channel name
                        self._pid_on(data[0], client_handler)
                    elif command == 'POF':
                        ### data : [0] (str)channel name
                        self._pid_off(data[0], client_handler)
                    elif command == 'FON':
                        ### data : [0] (str)channel name
                        self._focus_on(data[0], client_handler)
                    elif command == 'FOF':
                        ### data : [0] (str)channel name
                        self._focus_off(data[0], client_handler)
                    elif command == 'AEN':
                        ### data : [0] (str)channel name
                        self._auto_exposure_on(data[0], client_handler)
                    elif command == 'AEF':
                        ### data : [0] (str)channel name
                        self._auto_exposure_off(data[0], client_handler)
                    elif command == 'WMS':
                        ### no data (empty list)
                        self._reply_current_status(client_handler)
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
                        # todo - exception
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
                        # todo - exception
                        pass
                else:
                    # todo - exception
                    pass

            self._thread_status = THREAD_STATUS["standby"]
            self._cond.wait(self._mutex)
            self._mutex.unlock()

class PIDLoop(QThread):
    signal_new_measured_data = pyqtSignal(str, float)   # channel name, current frequency
    signal_new_exposure_time = pyqtSignal(str, int)     # channel name, exposure time
    signal_new_output = pyqtSignal(str, float)          # channel name, output voltage
    signal_new_apd_value = pyqtSignal(str, list)        # channel name, [accumulator, proportional, differentiator]

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.is_running = False
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()

        self.signal_new_measured_data.connect(self.controller._update_current_frequency)
        self.signal_new_exposure_time.connect(self.controller._update_exposure_time)
        self.signal_new_output.connect(self.controller._update_output_voltage)
        self.signal_new_apd_value.connect(self.controller._inform_apd_value)

    def _measure_frequency(self, channel_name, channel_obj):
        self.controller.wavemeter.set_switch_channel(channel_obj.fiber_switch)
        total_exposure = channel_obj.exposure_time + self.controller.wavemeter.switch_delay
        self.time_consumed += total_exposure
        time.sleep(0.001 * total_exposure)

        current_frequency = self.controller.wavemeter.get_current_frequency(channel_obj.fiber_switch)
        previous_weighted_frequency = channel_obj.weighted_frequency
        previous_time = channel_obj.current_time
        channel_obj.current_time = time.time()
        # todo - debug self.signal_new_measured_data.emit(channel_name, current_frequency)
        self.controller._update_current_frequency(channel_name, current_frequency)

        if current_frequency == 0:
            ### No signal
            # todo - exception
            return
        elif current_frequency == -3:
            ###
            if channel_obj.auto_exposure_on:
                new_exp = int(channel_obj.exposure_time * self.controller.auto_exposure_step)
                if new_exp > self.controller.wavemeter.cExposureMax:
                    new_exp = self.controller.wavemeter.cExposureMax
                # todo - debug self.signal_new_exposure_time.emit(channel_name, new_exp)
                self.controller._update_exposure_time(channel_name, new_exp)
            return
        elif current_frequency == -4:
            ###
            if channel_obj.auto_exposure_on:
                new_exp = int(channel_obj.exposure_time / self.controller.auto_exposure_step)
                if new_exp < self.controller.wavemeter.cExposureMin:
                    new_exp = self.controller.wavemeter.cExposureMin
                # todo - debug self.signal_new_exposure_time.emit(channel_name, new_exp)
                self.controller._update_exposure_time(channel_name, new_exp)
            return

        ### If the frequency changes abruptly (more than 1 GHz), set weighted frequency equal to
        ### the current freuqency. Otherwise, apply weight 0.9 to the current frequency and 0.1 to
        ### the previous weighted frequency.
        if abs(channel_obj.current_frequency - channel_obj.weighted_frequency) > 0.001:
            channel_obj.weighted_frequency = channel_obj.current_frequency
        else:
            channel_obj.weighted_frequency \
                = channel_obj.current_frequency * 0.9 + channel_obj.weighted_frequency * 0.1

        if not channel_obj.pid_on:
            return

        frequency_offset = channel_obj.weighted_frequency - channel_obj.target_frequency
        if frequency_offset > self.controller.max_frequency_offset:
            frequency_offset = self.controller.max_frequency_offset

        delta_t = channel_obj.current_time - previous_time
        delta_f = channel_obj.weighted_frequency - previous_weighted_frequency
        if delta_f > self.controller.max_frequency_change:
            delta_f = self.controller.max_frequency_change

        channel_obj.accumulator = channel_obj.accumulator + channel_obj.ii * frequency_offset * delta_t
        channel_obj.proportional = channel_obj.pp * frequency_offset
        channel_obj.differentiator = channel_obj.dd * delta_f / delta_t
        new_output = channel_obj.recent_output_voltage + \
            (channel_obj.accumulator + channel_obj.proportional + channel_obj.differentiator) * channel_obj.gain
        # todo - debug self.signal_new_output.emit(channel_name, new_output)
        # todo - debugself.signal_new_apd_value.emit(channel_name, [channel_obj.accumulator, channel_obj.proportional, \
        #    channel_obj.differentiator])

        self.controller._update_output_voltage(channel_name, new_output)
        self.controller._inform_apd_value(channel_name, [channel_obj.accumulator, channel_obj.proportional, \
            channel_obj.differentiator])

    def activate_loop(self):
        """ Starting the loop. Starting measurement should be done externally. """
        self.is_running = True
        self.wait_condition.wakeAll()

    def inactivate_loop(self):
        """ Stopping the loop. Stopping measurement should be done externally. """
        self.is_running = False

    def run(self):
        last_time = time.time()
        while True:
            self.time_consumed = 0
            self.mutex.lock()
            if self.is_running and self.controller._channel_list_prio_high:
                ### Case where some channel is focused.
                ### There should be only one channel in self.controller._channel_list_prio_high
                focused_flag = True
                for channel_name, channel_obj in self.controller._channel_list_prio_high.items():
                    self.time_consumed += self.controller.switch_safe
                    time.sleep(0.001 * self.controller.switch_safe)

                    if not channel_obj.monitor_list:
                        ### If the focused channel has no monitoring client, focus off it
                        self.controller._focus_off(channel_name)
                        continue

                    self._measure_frequency(channel_name, channel_obj)
                    break
            elif self.is_running and not self.controller._channel_list_prio_high:
                ### Case where no channel is focused.
                focused_flag = False
                monitor_exist = False
                for channel_name, channel_obj in self.controller._channel_list_prio_low.items():
                    self.time_consumed += self.controller.switch_safe
                    time.sleep(0.001 * self.controller.switch_safe)

                    if not channel_obj.monitor_list:
                        continue
                    
                    monitor_exist = True
                    self._measure_frequency(channel_name, channel_obj)

                if not monitor_exist:
                    self.inactivate_loop()
            else:
                self.wait_condition.wait(self.mutex)
                self.mutex.unlock()
                continue
            if self.time_consumed < 1000 and not focused_flag:
                time.sleep(1 - 0.001 * self.time_consumed)
            self.mutex.unlock()

class Channel():
    """ Logical class representing the laser. """
    def __init__(self, laser_name, exposure_time, pid, fiber_switch, DAC_channel, target_frequency):
        ### pid : list of [0]P, [1]I, [2]D, [3]gain
        self.name = laser_name
        self.monitor_list = []
        self.fiber_switch = fiber_switch
        self.DAC_channel = DAC_channel

        self.target_frequency = target_frequency
        self.current_frequency = float(0.0)
        self.weighted_frequency = float(0.0)
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

    def add_monitor_client(self, client_name):
        """ Add new subscriber client to the monitor list """
        if client_name in self.monitor_list:
            return

        self.monitor_list.append(client_name)

    def remove_monitor_client(self, client_name):
        """ Unsubscribe the specified client from the channel """
        if client_name not in self.monitor_list:
            return

        self.monitor_list.remove(client_name)

        ### For the unused channel, turn off pid and auto exposure
        if not self.monitor_list:
            self.auto_exposure_on = False
            self.pid_on = False

class Client():
    """ Logical class representing the client. """
    def __init__(self, client_name, communication_handler):
        self.name = client_name
        self.communcation_handler = communication_handler
        self.channel_list = []

    def send_message(self, message):
        self.communcation_handler.toMessageList(message)

    def subscribe_channel(self, channel_name):
        """ Add the name of the channel that the client newly subscribe to. """
        self.channel_list.append(channel_name)

    def unsubscribe_channel(self, channel_name):
        """ Remove the name of the channel that the client want to unsubscribe. """
        if channel_name in self.channel_list:
            self.channel_list.remove(channel_name)

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

if __name__ == "__main__":
    controller = WavemeterController()
