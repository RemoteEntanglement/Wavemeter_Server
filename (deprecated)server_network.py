from PyQt5.QtCore import QByteArray, QDataStream, QHistoryState, QIODevice
from PyQt5.QtNetwork import QHostAddress, QTcpServer

class ServerSocket(QTcpServer):
    def __init__ (self, controller):
        super().__init__()
        self.controller = controller

    def _handle_new_client(self):
        client_socket = self.nextPendingConnection()
        self.client_list.append(ClientHandler(client_socket))

    def open_session(self, ip, port):
        # todo - check whether channel list is non-empty in controller?

        if self.isListening():
            # error - already listening
            return -1

        host = QHostAddress(ip)

        if not self.listen(host, port):
            # error - listening fail
            return -1

        self.newConnection.connect(self._handle_new_client)

        return 0

    def close_session(self):
        # todo
        pass

    def broadcast_message(self, message, exception=[]):
        # todo
        pass

    def send_message_to_specific_clients(self, message, client_list):
        # todo
        pass

class ClientHandler():
    def __init__ (self, client_socket):
        super().__init__()
        self.socket = client_socket

    def send_message(self, message):
        if not self.socket.isOpen():
            # error - disconnected
            return -100
        
        try:
            command = message[0]
            control = message[1]
            data = message[2]
        except:
            # error - message of non-list type
            return -1

        output_block = QByteArray()
        output_stream = QDataStream(output_block, QIODevice.WriteOnly)
        output_stream.setVersion(QDataStream.Qt_5_0)

        output_stream.writeUInt16(0)
        output_stream.writeQString(command)
        output_stream.writeQString(control)
        output_stream.writeQVariantList(data)
        output_stream.device().seek(0)
        block_size = output_block.size()-2
        output_stream.writeUInt16(block_size)

        self.socket.write(output_block)
        return block_size

    def receive_message(self):
        input_stream = QDataStream(self.socket)
        input_stream.setVersion(QDataStream.Qt_5_0)

        while True:
            if self.block_size == 0:
                if self.socket.bytesAvailable() < 2:
                    return
                self.block_size = input_stream.readUInt16()
            if self.socket.bytesAvailable() < self.block_size:
                return

            control = str(input_stream.readQString())
            command = str(input_stream.readQString())
            data = list(input_stream.readQVariantList())
            self.block_size = 0

            # todo - 'CON' message should be handled here to enroll the user name

            # todo -self.controller.handle_message_from_server([control, command, data])
