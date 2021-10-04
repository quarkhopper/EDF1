import inspect
import time
import uuid
import textwrap


class EventInvoker:
    """
    Class to define the criteria and behavior for invoking this action
    """
    def __init__(self, poll_action, do_once=False, timeout=10, poll_sleep=1):
        self.do_once = do_once
        self.timeout = timeout
        self.poll_sleep = poll_sleep
        self.poll_action = poll_action
        self.activation_time = 0
        self.exception = None

    def activate(self, event) -> 'EventMessage':
        """
        Run and interpret the delegate function that determines whether to invoke this event. This is the primary source
        of messaging that ends up passed up from the event and calling method.
        :param event: the calling event
        :return:
        """
        self.activation_time = time.time()
        while self.timeout == 0 or time.time() - self.activation_time < self.timeout:
            try:
                data = self.poll_action()
                success = data is not False
            except Exception as ex:
                exception = Exception(f"[INVOKER] polling failed", ex)
                return EventMessage(event_name=event.name, success=False, exception=exception)
            if not success:
                if self.do_once:
                    return EventMessage(event_name=event.name, success=False)
                time.sleep(self.poll_sleep)
            else:
                return EventMessage(event_name=event.name, data=data)
        if self.timeout > 0:
            exception = Exception(f"[INVOKER] timeout on poll action. timeout: {self.timeout}")
            return EventMessage(event_name=event.name, success=False, exception=exception)


class EventCallback:
    """
    Wrapper for callback methods from subscribed observers
    """

    def __init__(self, callback, invoke_once=True):
        self.invoke_once = invoke_once
        self.callback = callback

    def activate(self, result):
        self.callback(result)


class EventMessage:
    """
    Standard formatter and container for messaging, data, and exception information that comes back from events
    """

    def __init__(self, event_name: str = None, caller: str = None, success: bool = True,
                 data: any = None, exception: Exception = None, inner_message: 'EventMessage' = None):
        self.id = uuid.uuid4()
        self.event_name = event_name
        self.caller = caller
        self.success = success
        self.data = data
        self.inner_message = inner_message
        self.exception = exception

    def to_string(self, indent=0):
        description = [
            f"[EVENT MESSAGE (id: {str(self.id)})] event: {self.event_name}",
            f"invoked by: {self.caller}",
            f"success: {self.success}",
        ]
        if self.exception:
            description.append(f"exception: {self.exception}")
        if self.data:
            description.append(f"data: {str(self.data)}")
        if self.inner_message:
            description.append("inner message:")
            description.append(textwrap.indent(self.inner_message.to_string(), '    '))

        return "\n".join(description)


class Event:
    """
    Class to define a unique signal that can be subscribed to by observing entities. Accepts an invoker that determines
    it's behavior, delegate callback function from subscribed observers, and passes back EventMessages
    """

    def __init__(self, name: str, tags=None):
        if tags is None:
            tags = []
        self.name = name
        self.tags = tags
        self.tags.append("all")
        self.callbacks = []

    def invoke(self, invoker: EventInvoker) -> EventMessage:
        current_frame = inspect.currentframe()
        caller_frame = inspect.getouterframes(current_frame, 2)
        caller = caller_frame[1][3]

        if invoker is None:
            message = EventMessage(self.name, caller=caller)
            self.execute_callbacks(message)
            return message
        else:
            message = invoker.activate(self)
            if message.success:
                message.caller = caller
                self.execute_callbacks(message)
                return message
            else:
                exception = Exception(f"[EVENT FAILED: {self.name}] invocation exception: {message.exception}")
                message.caller = caller
                self.execute_callbacks(message)
                return message

    def invoke_with_inner_message(self, inner_message: EventMessage):
        message = EventMessage(self.name, caller=inner_message.event_name, inner_message=inner_message)
        self.execute_callbacks(message)
        return message

    def execute_callbacks(self, message):
        for callback in self.callbacks:
            callback.activate(message)

        updated_callbacks = []
        for callback in self.callbacks:
            if not callback.invoke_once:
                updated_callbacks.append(callback)
        self.callbacks = updated_callbacks

    def observe(self, callback_method):
        """
        set up a continual callback for the event
        :param callback_method: method to invoke on callback
        :return: None
        """
        self.subscribe(EventCallback(callback_method, invoke_once=False))

    def respond(self, callback_method):
        """
        set up a one time callback for the event
        :param callback_method:
        :return:
        """
        self.subscribe(EventCallback(callback_method))

    def subscribe(self, callback: EventCallback):
        self.callbacks.append(callback)

    def subscribe_event(self, event: 'Event'):
        callback = EventCallback((lambda message: event.invoke_with_inner_message(message)), invoke_once=False)
        self.subscribe(callback)
