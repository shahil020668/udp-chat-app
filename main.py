from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty
from kivy.utils import platform
from kivy.core.window import Window
import socket
from threading import Thread
from datetime import datetime

# Android permissions
if platform == 'android':
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([Permission.INTERNET])
    except Exception:
        pass

Builder.load_file('mymessenger.kv')

class MessageBubble(BoxLayout):
    sender = StringProperty('')
    message = StringProperty('')
    timestamp = StringProperty('')
    text_color = ListProperty([0.1, 0.1, 0.1, 1])
    bubble_color = ListProperty([0.9, 0.9, 0.9, 1])

class EmptyBox(BoxLayout):
    pass

class ChatLayout(BoxLayout):
    show_connect_box = BooleanProperty(True)
    connected = BooleanProperty(False)
    emptybox_visible = BooleanProperty(False)
    emptybox_height = NumericProperty(dp(300))  # Increased height

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = None
        self.nickname = ""
        Clock.schedule_once(self.bind_input_focus)

    def bind_input_focus(self, dt):
        self.ids.text_input.bind(focus=self.on_input_focus)

    def on_input_focus(self, instance, value):
        if value:  # Focused (keyboard up)
            self.emptybox_visible = True
            # Scroll to bottom after the emptybox is visible
            def scroll_down(dt):
                self.ids.scroll_view.scroll_y = 0
            Clock.schedule_once(scroll_down, 0.1)
        else:  # Unfocused (keyboard down)
            self.emptybox_visible = False

    def connect(self):
        self.nickname = self.ids.nickname_input.text.strip()
        if not self.nickname:
            self.add_message("[System]", "Nickname is required", (0.8, 0.2, 0.2, 1))
            return

        self.ids.connect_btn.disabled = True
        self.ids.nickname_input.disabled = True
        self.add_message("[System]", "Connecting...", (0.2, 0.6, 0.8, 1))

        def do_connect():
            try:
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client.connect(('192.168.99.94', 55555))
                self.client.send(self.nickname.encode('ascii'))
                Thread(target=self.receive_messages, daemon=True).start()
                def update_ui(dt):
                    self.show_connect_box = False
                    self.connected = True
                    self.add_message("[System]", f"Connected as {self.nickname}", (0.2, 0.6, 0.2, 1))
                Clock.schedule_once(update_ui)
            except Exception as e:
                def retry_ui(dt):
                    self.ids.connect_btn.disabled = False
                    self.ids.nickname_input.disabled = False
                    self.add_message("[Error]", "Server unreachable. Please check your connection.", (0.8, 0.2, 0.2, 1), show_retry=True)
                Clock.schedule_once(retry_ui)
        Thread(target=do_connect, daemon=True).start()

    def add_message(self, sender, message, color=(0.1, 0.1, 0.1, 1), show_retry=False):
        def add(dt):
            if sender == "[You]":
                bubble_color = [0.2, 0.6, 0.8, 0.15]
                text_color = [0.2, 0.4, 0.8, 1]
            elif sender == "[System]" or sender == "[Error]":
                bubble_color = [1, 0.95, 0.8, 1]
                text_color = color
            else:
                bubble_color = [0.9, 0.9, 0.9, 1]
                text_color = color

            bubble = MessageBubble(sender=sender, message=message, timestamp=self.get_time(), text_color=text_color, bubble_color=bubble_color)
            self.ids.chat_container.add_widget(bubble)  # add at end
            #Clock.schedule_once(lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 1))  # scroll to top (bottom of view)
            if show_retry:
                retry_btn = Button(
                    text="Try Again",
                    size_hint_y=None,
                    height=dp(40),
                    background_color=(0.8, 0.2, 0.2, 1),
                    color=(1, 1, 1, 1)
                )
                retry_btn.bind(on_release=lambda x: self.connect())
                self.ids.chat_container.add_widget(retry_btn)
           # Clock.schedule_once(lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 0))  # scroll to top
        Clock.schedule_once(add)

    def send_message(self):
        message = self.ids.text_input.text.strip()
        self.ids.text_input.text = ''
        if not message or not self.connected:
            self.add_message("[System]", "You must connect first", (0.8, 0.2, 0.2, 1))
            return
        try:
            self.client.send(message.encode('ascii'))
            self.add_message("[You]", message, (0.2, 0.4, 0.8, 1))
        except Exception as e:
            self.add_message("[Error]", f"Send failed: {str(e)}", (0.8, 0.2, 0.2, 1))
            self.connected = False
            self.show_connect_box = True

    def receive_messages(self):
        while True:
            try:
                message = self.client.recv(1024).decode('ascii', errors='ignore')
                if not message:
                    break
                if message == 'NICK':
                    self.client.send(self.nickname.encode('ascii'))
                else:
                    self.add_message("[Server]", message)
            except Exception as e:
                self.add_message("[Error]", f"Connection lost: {str(e)}", (0.8, 0.2, 0.2, 1))
                self.connected = False
                self.show_connect_box = True
                break

    def get_time(self):
        return datetime.now().strftime("%H:%M:%S")

clients = []

def broadcast(message, sender_socket=None):
    for client in clients:
        if client != sender_socket:
            try:
                client.send(message)
            except:
                client.close()
                clients.remove(client)

def handle_client(client):
    while True:
        try:
            message = client.recv(1024)
            broadcast(message, sender_socket=client)
        except:
            clients.remove(client)
            client.close()
            break

class ChatApp(App):
    def build(self):
        self.title = "MyMessenger"
        return ChatLayout()

if __name__ == '__main__':
    ChatApp().run()