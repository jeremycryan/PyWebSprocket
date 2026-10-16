import asyncio
import platform

from py_sprocket_web.packet import Packet
import py_sprocket_web.network_constants as nc


class WebSprocket:
    """
    Client-side websocket (WebSprocket) interface. Connects to an open server (WebServo) if able, then puts all
    traffic into a queue the user can check later.

    MUST be running in a Python WASM (Pygbag) context since this uses JS bindings with no fallback. Also MUST be
    initialized from an async/await context, as is already required by Pygbag.
    """

    INITIALIZING = 0
    CONNECTED = 1
    DISCONNECTED = 2

    def __init__(self, host_addr, silent = False):
        """
        Initializes the WebSprocket.
        :param host_addr: The public URL of the server we're connecting to via web sockets
        """
        self.silent = silent
        self.log("WebSprocket object created.")

        self.status = self.INITIALIZING
        self.host_addr = host_addr

        self.queue = None
        self.sock = None

    def _init_websocket(self):
        """ Initialize the web socket connection and start listening to web socket events. """
        try:
            self.log("Start WebSprocket initialization.")
            window = platform.window
            self.sock = window.eval(f'new WebSocket("{self.host_addr}");')

            # Hook Python methods to JS events
            self.sock.onmessage = self._handle_incoming_packet
            self.sock.onopen = self._handle_open
            self.sock.onclose = self._handle_close
            self.sock.onerror = self._handle_close

        except Exception as e:
            self.log(f"Failed to create WebSprocket: {e}")
            self._on_connection_fail()

    def _handle_open(self, event):
        """ Called when connection is established to Servo. """
        self.status = self.CONNECTED
        self.log("WebSocket connection established successfully.")

    def _handle_close(self, event):
        """ Called when connection with Servo is closed. """
        self._on_connection_fail()

    def _handle_incoming_packet(self, event):
        """ Processes an incoming Packet from the server. """
        data = event.data

        try:
            packet = Packet.from_json(data)
            self.log(f"Received: {data}")
            if packet.is_ping():
                self.send_packet(Packet.pong())
                return
            self.queue.put_nowait(packet)
        except Exception as e:
            self.log(f"Error parsing incoming WebSprocket Packet: {e}")

    def _on_connection_fail(self):
        """ Called when we fail to connect to the WebServo. """
        self.status = self.DISCONNECTED
        self.log("WebSprocket state set to DISCONNECTED.")
        self.sock = None

    def log(self, string):
        """ Logs a message to the browser console. """
        if self.silent:
            return
        platform.console.log(string)

    # =========================================================================
    # PUBLIC METHODS (Safe to call inside your main update loop)
    #    start -> Starts up the WebSprocket connection and connects to the WebServo
    #    is_ready -> Returns False if the Sprocket is not ready to send data yet, or if it has been disconnected
    #    get -> Gets all messages that have been received since you last checked
    #    send/send_packet -> Sends data to the Servo
    # =========================================================================

    async def start(self):
        """
        Connects the Sprocket to the Servo and starts listening for incoming messages.
        MUST be awaited in an async context.
        """

        await asyncio.sleep(0)  # Important to do this before we instantiate a queue to make sure async has started
        self.queue = asyncio.Queue()

        if nc.IS_WEB:
            self._init_websocket()
        else:
            self._on_connection_fail()

    def get(self):
        """ Returns a list of Packet objects that have been received since the last check. """
        response = []
        if not self.queue:
            return response

        while not self.queue.empty():
            try:
                response.append(self.queue.get_nowait())
            except Exception:
                break
        return response

    def send_packet(self, packet_object):
        """ Sends a Packet object to the WebServo. """
        if not self.is_ready():
            self.log("Cannot send packet: WebSprocket is not open.")
            return

        data = packet_object.to_json()
        self.sock.send(data)
        self.log(f"Sent: {data}")

    def send(self, **kwargs):
        """ Constructs a Packet from keyword arguments and sends it to the WebServo. """
        self.send_packet(Packet(**kwargs))

    def is_ready(self):
        """
        Returns True if the WebSprocket is ready to send data. If you attempt to
        send data before this method returns True, it will fail.
        """
        if self.status != self.CONNECTED or self.sock is None or self.sock.readyState != 1:
            return False
        return True
