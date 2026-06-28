from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.relativelayout import RelativeLayout
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Ellipse
from kivy.utils import get_color_from_hex
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp
import socketio
import requests
from datetime import datetime

Window.size = (400, 700)
Window.clearcolor = get_color_from_hex('#0F0F0F')

SERVER_URL = ""
current_user = ""
current_chat = "general"
sio = socketio.Client()

TG_BLUE = get_color_from_hex('#0088CC')
TG_MSG_ME = get_color_from_hex('#0088CC')
TG_MSG_OTHER = get_color_from_hex('#1C1C1E')
TG_TEXT = get_color_from_hex('#FFFFFF')
TG_GRAY = get_color_from_hex('#8E8E93')

class Avatar(Widget):
    def __init__(self, text='?', size=50, **kwargs):
        super().__init__(**kwargs)
        self.size = (dp(size), dp(size))
        self.text = text[:2].upper()
        self.colors = [
            get_color_from_hex('#FF6B6B'), get_color_from_hex('#4ECDC4'),
            get_color_from_hex('#45B7D1'), get_color_from_hex('#96CEB4'),
            get_color_from_hex('#FFEAA7'), get_color_from_hex('#DDA0DD'),
        ]
        self.color = self.colors[hash(text) % len(self.colors)]
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        self.label = None
        Clock.schedule_once(self.add_label, 0.1)
    
    def add_label(self, dt):
        self.label = Label(
            text=self.text,
            color=(1,1,1,1),
            font_size=self.width * 0.4,
            pos=self.pos,
            size=self.size,
            halign='center',
            valign='middle'
        )
        self.parent.add_widget(self.label)
    
    def update_canvas(self, *args):
        if hasattr(self, 'label') and self.label:
            self.label.pos = self.pos
            self.label.size = self.size
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.color)
            Ellipse(pos=self.pos, size=self.size)

class ChatItem(ButtonBehavior, BoxLayout):
    def __init__(self, username, display_name, status='offline', **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(65)
        self.padding = [dp(10), dp(5)]
        self.username = username
        
        avatar = Avatar(text=display_name or username, size=45)
        avatar.pos = (dp(10), dp(10))
        self.add_widget(avatar)
        
        info = BoxLayout(orientation='vertical', size_hint_x=0.8, padding=[dp(15), dp(5)])
        name = Label(
            text=display_name or username,
            color=TG_TEXT,
            font_size=16,
            halign='left',
            size_hint_y=0.6
        )
        info.add_widget(name)
        
        status_text = '🟢 Онлайн' if status == 'online' else '⚪ Офлайн'
        status_label = Label(
            text=status_text,
            color=TG_GRAY,
            font_size=12,
            halign='left',
            size_hint_y=0.4
        )
        info.add_widget(status_label)
        
        self.add_widget(info)
    
    def on_press(self):
        global current_chat
        current_chat = self.username
        app = App.get_running_app()
        app.root.get_screen('chat').load_chat(self.username)

class ChatsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(size_hint_y=None, height=dp(65), padding=[dp(15), dp(10)])
        with header.canvas.before:
            Color(*get_color_from_hex('#1C1C1E'))
            self.header_rect = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self.update_rect, size=self.update_rect)
        
        title = Label(
            text='💬 Maka',
            color=TG_TEXT,
            font_size=24,
            halign='left',
            size_hint_x=0.7
        )
        header.add_widget(title)
        
        btn_logout = Button(
            text='🚪',
            size_hint_x=0.15,
            background_color=(0,0,0,0),
            color=TG_BLUE,
            font_size=20
        )
        btn_logout.bind(on_press=self.do_logout)
        header.add_widget(btn_logout)
        
        layout.add_widget(header)
        
        self.scroll = ScrollView()
        self.chats_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        self.chats_container.bind(minimum_height=self.chats_container.setter('height'))
        self.scroll.add_widget(self.chats_container)
        layout.add_widget(self.scroll)
        
        self.add_widget(layout)
    
    def update_rect(self, instance, value):
        self.header_rect.pos = instance.pos
        self.header_rect.size = instance.size
    
    def on_enter(self):
        self.load_chats()
    
    def load_chats(self):
        self.chats_container.clear_widgets()
        try:
            response = requests.get(f"{SERVER_URL}/api/users?exclude={current_user}", timeout=5)
            users = response.json().get('users', [])
            
            general = ChatItem('general', 'Общий чат', 'online')
            general.bind(on_press=lambda x: self.open_chat('general'))
            self.chats_container.add_widget(general)
            
            for user in users:
                chat = ChatItem(user['username'], user['display_name'], user.get('status', 'offline'))
                self.chats_container.add_widget(chat)
                
        except Exception as e:
            print(f'Ошибка загрузки: {e}')
    
    def open_chat(self, chat_id):
        global current_chat
        current_chat = chat_id
        self.manager.current = 'chat'
        self.manager.get_screen('chat').load_chat(chat_id)
    
    def do_logout(self, instance):
        self.manager.current = 'login'
        self.manager.get_screen('login').error.text = '👋 Выход выполнен'

class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        main = BoxLayout(orientation='vertical')
        
        header = BoxLayout(size_hint_y=None, height=dp(65), padding=[dp(10), dp(10)])
        with header.canvas.before:
            Color(*get_color_from_hex('#1C1C1E'))
            self.header_rect = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self.update_rect, size=self.update_rect)
        
        btn_back = Button(
            text='←',
            size_hint_x=0.1,
            background_color=(0,0,0,0),
            color=TG_BLUE,
            font_size=24
        )
        btn_back.bind(on_press=self.go_back)
        header.add_widget(btn_back)
        
        self.chat_title = Label(
            text='Чат',
            color=TG_TEXT,
            font_size=18,
            size_hint_x=0.7,
            halign='center'
        )
        header.add_widget(self.chat_title)
        
        self.header_avatar = Avatar(text='M', size=35)
        self.header_avatar.pos = (header.width - dp(50), dp(15))
        header.add_widget(self.header_avatar)
        
        main.add_widget(header)
        
        self.scroll = ScrollView()
        self.msg_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=3,
            padding=[dp(10), dp(10)]
        )
        self.msg_container.bind(minimum_height=self.msg_container.setter('height'))
        self.scroll.add_widget(self.msg_container)
        main.add_widget(self.scroll)
        
        input_box = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(5), padding=[dp(10), dp(5)])
        with input_box.canvas.before:
            Color(*get_color_from_hex('#1C1C1E'))
            self.input_rect = RoundedRectangle(pos=input_box.pos, size=input_box.size)
        input_box.bind(pos=self.update_input_rect, size=self.update_input_rect)
        
        self.input = TextInput(
            multiline=False,
            hint_text='Сообщение...',
            size_hint_x=0.8,
            background_color=(0.15,0.15,0.17,1),
            foreground_color=TG_TEXT,
            hint_text_color=TG_GRAY,
            font_size=16,
            padding=[dp(15), dp(10)]
        )
        self.input.bind(on_text_validate=self.send_msg)
        
        btn_send = Button(
            text='➤',
            size_hint_x=0.15,
            background_color=TG_BLUE,
            color=TG_TEXT,
            font_size=20,
            background_normal=''
        )
        btn_send.bind(on_press=self.send_msg)
        
        input_box.add_widget(self.input)
        input_box.add_widget(btn_send)
        main.add_widget(input_box)
        
        self.add_widget(main)
    
    def update_rect(self, instance, value):
        self.header_rect.pos = instance.pos
        self.header_rect.size = instance.size
    
    def update_input_rect(self, instance, value):
        self.input_rect.pos = instance.pos
        self.input_rect.size = instance.size
    
    def load_chat(self, chat_id):
        self.chat_title.text = chat_id.capitalize()
        self.header_avatar.text = chat_id[:2].upper()
        self.msg_container.clear_widgets()
        self.load_history(chat_id)
        
        try:
            sio.connect(SERVER_URL)
            sio.emit('join', {'room': chat_id, 'username': current_user})
        except:
            pass
        
        @sio.on('new_message')
        def on_msg(data):
            is_self = data['sender'] == current_user
            self.add_message(data['sender'], data['content'], data['time'], is_self)
        
        @sio.on('user_typing')
        def on_typing(data):
            self.chat_title.text = f'✏️ {data["username"]} печатает...'
            Clock.schedule_once(lambda dt: setattr(self.chat_title, 'text', 'Чат'), 2)
    
    def load_history(self, chat_id):
        try:
            resp = requests.get(f"{SERVER_URL}/api/messages/{chat_id}")
            for msg in resp.json().get('messages', []):
                is_self = msg['sender'] == current_user
                self.add_message(msg['sender'], msg['content'], msg['time'], is_self, from_history=True)
        except:
            pass
    
    def add_message(self, sender, content, time, is_self=False, from_history=False):
        msg_box = RelativeLayout(size_hint_y=None, height=dp(35))
        
        if is_self:
            msg_box.height = max(dp(35), len(content) // 20 * dp(20) + dp(20))
            pos_hint = {'right': 1}
            halign = 'right'
        else:
            msg_box.height = max(dp(35), len(content) // 20 * dp(20) + dp(20))
            pos_hint = {'left': 1}
            halign = 'left'
        
        bubble = Label(
            text=content,
            color=TG_TEXT,
            font_size=14,
            size_hint=(0.7, 1),
            pos_hint=pos_hint,
            halign=halign,
            valign='middle',
            padding=[dp(12), dp(8)]
        )
        bubble.bind(texture_size=self.update_bubble)
        msg_box.add_widget(bubble)
        
        time_label = Label(
            text=time,
            color=TG_GRAY,
            font_size=10,
            size_hint=(0.15, 0.3),
            pos_hint={'right' if is_self else 'left': 0.72 if is_self else 0.03, 'y': 0.65}
        )
        msg_box.add_widget(time_label)
        
        self.msg_container.add_widget(msg_box)
        
        if not from_history:
            Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)
    
    def update_bubble(self, instance, value):
        instance.parent.height = max(dp(35), value[1] + dp(16))
    
    def send_msg(self, instance):
        text = self.input.text.strip()
        if text:
            sio.emit('message', {
                'room': current_chat,
                'sender': current_user,
                'content': text
            })
            self.input.text = ''
            self.add_message(current_user, text, datetime.now().strftime('%H:%M'), is_self=True)
            sio.emit('typing', {'room': current_chat, 'username': current_user})
    
    def go_back(self, instance):
        self.manager.current = 'chats'

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', spacing=15, padding=[dp(40), dp(60)])
        
        layout.add_widget(Label(
            text='💬 Maka',
            font_size=50,
            color=TG_BLUE,
            size_hint_y=0.2
        ))
        layout.add_widget(Label(
            text='Введите адрес сервера',
            font_size=14,
            color=TG_GRAY,
            size_hint_y=0.05
        ))
        
        self.url_input = TextInput(
            hint_text='https://xxxx.serveo.net',
            multiline=False,
            size_hint_y=None,
            height=dp(50),
            background_color=(0.1,0.1,0.12,1),
            foreground_color=TG_TEXT,
            hint_text_color=TG_GRAY,
            padding=[dp(15), dp(10)]
        )
        layout.add_widget(self.url_input)
        
        layout.add_widget(Label(
            text='Имя пользователя',
            font_size=14,
            color=TG_GRAY,
            size_hint_y=0.05
        ))
        self.username = TextInput(
            hint_text='Ваше имя',
            multiline=False,
            size_hint_y=None,
            height=dp(50),
            background_color=(0.1,0.1,0.12,1),
            foreground_color=TG_TEXT,
            hint_text_color=TG_GRAY,
            padding=[dp(15), dp(10)]
        )
        layout.add_widget(self.username)
        
        layout.add_widget(Label(
            text='Пароль',
            font_size=14,
            color=TG_GRAY,
            size_hint_y=0.05
        ))
        self.password = TextInput(
            hint_text='Пароль',
            password=True,
            multiline=False,
            size_hint_y=None,
            height=dp(50),
            background_color=(0.1,0.1,0.12,1),
            foreground_color=TG_TEXT,
            hint_text_color=TG_GRAY,
            padding=[dp(15), dp(10)]
        )
        layout.add_widget(self.password)
        
        btn_login = Button(
            text='Войти',
            size_hint_y=None,
            height=dp(50),
            background_color=TG_BLUE,
            color=TG_TEXT,
            font_size=16
        )
        btn_login.bind(on_press=self.do_login)
        layout.add_widget(btn_login)
        
        btn_register = Button(
            text='Регистрация',
            size_hint_y=None,
            height=dp(40),
            background_color=(0,0,0,0),
            color=TG_BLUE,
            font_size=14
        )
        btn_register.bind(on_press=self.do_register)
        layout.add_widget(btn_register)
        
        self.error = Label(text='', color=(1,0,0,1), font_size=14)
        layout.add_widget(self.error)
        
        self.add_widget(layout)
    
    def do_login(self, instance):
        global SERVER_URL, current_user
        SERVER_URL = self.url_input.text.strip().rstrip('/')
        username = self.username.text.lower().strip()
        password = self.password.text
        
        try:
            response = requests.post(f"{SERVER_URL}/api/login", json={
                'username': username,
                'password': password
            }, timeout=5)
            data = response.json()
            
            if data.get('success'):
                current_user = username
                self.error.text = '✅ Вход выполнен!'
                self.manager.current = 'chats'
                self.manager.get_screen('chats').load_chats()
            else:
                self.error.text = '❌ ' + data.get('message', 'Ошибка')
        except:
            self.error.text = '❌ Сервер недоступен'
    
    def do_register(self, instance):
        global SERVER_URL
        SERVER_URL = self.url_input.text.strip().rstrip('/')
        username = self.username.text.lower().strip()
        password = self.password.text
        
        if len(username) < 3:
            self.error.text = '❌ Минимум 3 символа'
            return
        
        try:
            response = requests.post(f"{SERVER_URL}/api/register", json={
                'username': username,
                'password': password
            }, timeout=5)
            data = response.json()
            
            if data.get('success'):
                self.error.text = '✅ ' + data.get('message', 'Успешно!')
            else:
                self.error.text = '❌ ' + data.get('message', 'Ошибка')
        except:
            self.error.text = '❌ Сервер недоступен'

class MakaApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(ChatsScreen(name='chats'))
        sm.add_widget(ChatScreen(name='chat'))
        return sm

if __name__ == '__main__':
    MakaApp().run()
