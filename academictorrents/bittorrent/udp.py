from tornado.iostream import IOStream

class UDPStream(IOStream):
    '''
    IOStream patched to correctly handle UDP sockets.
    '''

    def connect(self, address, callback=None, server_hostname=None):
        # This does no IO in the first place, so we don't need to hook it
        # up into the IOLoop
        self.socket.connect(address)

    def _handle_connect(self):
        # This should never be called
        pass
