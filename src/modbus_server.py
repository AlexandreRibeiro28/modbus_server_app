#!/usr/bin/env python3
__author__ = 'Alexandre Ribeiro'

import yaml
import os
import math
import sys

from pymodbus.server import StartAsyncTcpServer, ServerAsyncStop
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.payload import BinaryPayloadBuilder

from threading import Thread
from time import sleep

from rich.console import Console

from textual.app import App, ComposeResult
from textual.widgets import Label, Button, Header, Footer, Input, Static, Select
from textual import on, events
from textual.containers import Horizontal, Container, ScrollableContainer
from textual.validation import ValidationResult, Validator
import numpy as np
from queue import Queue
import csv

setting_dir = os.path.dirname(__file__)
rel_path_settings = "../settings/template_settings.yaml"
rel_path_css = "../settings/modbus_server.css"
rel_path_csv = "../data/watch_window_data.csv"
rel_path_logic = "../settings/logic.txt"
abs_file_path = os.path.join(setting_dir, rel_path_settings)

with open(abs_file_path, 'r') as file:
    server_settings = yaml.safe_load(file)

with open(rel_path_logic, 'r') as file:
    logic_txt = file.read()

TEXT = """\
self.query_one('#txt', Label).update("Deu certo")
M[3] = M[1] and M[2]
D[4] = D[1] + D[2]
D[5] = D[4] * 3
"""
queueCmdModbus = Queue()
queueMessageBetweenScreens = Queue()
queueM = Queue()
queueD = Queue()
queueM_logic = Queue()
queueD_logic = Queue()
global count_holding_register
global count_coils
count_holding_register = server_settings['data_block']['holding_registers']['qty']
count_coils = server_settings['data_block']['coils']['qty']
values_holding_registers = []
values_coils = []
global ip 
global port
global vendor_name
global product_code
global vendor_url
global product_name
global model_name
global major_minor_revision
ip = server_settings['identification']['ip_address']                          
port = server_settings['identification']['port']
vendor_name = server_settings['identification']['vendor_name']
product_code = server_settings['identification']['product_code']
vendor_url = server_settings['identification']['vendor_url']
product_name = server_settings['identification']['product_name']
model_name = server_settings['identification']['model_name']
major_minor_revision = server_settings['identification']['major_minor_revision']
watchTableSize = server_settings['data_block']['watch_window_size']

def endian_format():
    if sys.platform == 'linux':
        return Endian.BIG
    elif sys.platform == 'win32':
        return Endian.BIG
    else:
        raise RuntimeError("Unsupported operating system: {}".format(sys.platform))
class ModbusServerUpdate():
    def __init__(self, ip, port) -> None:
        self.ip = ip
        self.port = port
        self.store = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [0]*(1+server_settings['data_block']['discrete_inputs']['qty'])),   # discret inputs
            co=ModbusSequentialDataBlock(0, [0]*(1+server_settings['data_block']['coils']['qty'])),   # coils
            hr=ModbusSequentialDataBlock(0, [0]*(3+server_settings['data_block']['holding_registers']['qty'])),   # holding registers
            ir=ModbusSequentialDataBlock(0, [0]*(1+server_settings['data_block']['input_registers']['qty'])))   # input registers
        #store.getValues(1,2,1)
        self.context = ModbusServerContext(slaves=self.store, single=True)
        self.identity = ModbusDeviceIdentification()
        self.identity.VendorName = vendor_name
        self.identity.ProductCode = product_code
        self.identity.VendorUrl = vendor_url
        self.identity.ProductName = product_name
        self.identity.ModelName = model_name
        self.identity.MajorMinorRevision = major_minor_revision
        
    def start_modbus_server(self):
        global server_is_running
        thread0 = Thread(target=self.update_modbus_server, args=(queueCmdModbus,))
        thread0.daemon = True
        thread0.start()
        self.server = StartAsyncTcpServer(
                    context=self.context,
                    identity=self.identity,
                    address=(self.ip, self.port)
                )
        return self.server
    

    def stop_modbus_server(self):
        ServerAsyncStop()


    def get_server_status(self):
        return self.server.is_running


    def update_modbus_server(self, queueCmdModbus):
        c = Console()
        value = 0
        global server_is_running
        sleep(1)
        while server_is_running:
            if not queueCmdModbus.empty():
                full_cmd = queueCmdModbus.get()
            else:
                full_cmd = ['','','']

            cmd = full_cmd[0]
            if len(full_cmd) > 1:
                cmd_arg_0 = full_cmd[1]
            if len(full_cmd) > 2:
                cmd_arg_1 = full_cmd[2]
            
            if cmd == 'write_c':
                cmd_arg_1 = [bool(int(cmd_arg_1))]
                self.store.setValues(5,int(cmd_arg_0),cmd_arg_1)
                value = self.store.getValues(1,int(cmd_arg_0),len(cmd_arg_1))
                value = [ bool(x) for x in value ]
            if cmd == 'set':
                cmd_arg_1 = [True]
                self.store.setValues(5,int(cmd_arg_0),cmd_arg_1)
                value = self.store.getValues(1,int(cmd_arg_0),len(cmd_arg_1))
                value = [ bool(x) for x in value ]
            if cmd == 'rst':
                cmd_arg_1 = [False]
                self.store.setValues(5,int(cmd_arg_0),cmd_arg_1)
                value = self.store.getValues(1,int(cmd_arg_0),len(cmd_arg_1))
                value = [ bool(x) for x in value ]
            elif cmd == 'write_mc':
                cmd_arg_1 = cmd_arg_1[1:-1]
                cmd_arg_1 = cmd_arg_1.split(",")
                cmd_arg_1 = [ int(x) for x in cmd_arg_1 ]
                self.store.setValues(0x0F,int(cmd_arg_0),cmd_arg_1)
                value = self.store.getValues(1,int(cmd_arg_0),len(cmd_arg_1))
            elif cmd == 'read_c':
                value = self.store.getValues(1,int(cmd_arg_0),int(cmd_arg_1))
                value = [ bool(x) for x in value ]
            elif cmd == 'read_hr':
                value = self.store.getValues(3,int(cmd_arg_0),int(cmd_arg_1))
            elif cmd == 'write_mhr':
                cmd_arg_1 = cmd_arg_1[1:-1]
                cmd_arg_1 = cmd_arg_1.split(",")
                cmd_arg_1 = [ int(x) for x in cmd_arg_1 ]
                self.store.setValues(0x10,int(cmd_arg_0), cmd_arg_1)
                value = self.store.getValues(3,int(cmd_arg_0),len(cmd_arg_1))
            elif cmd == 'write_hr':
                cmd_arg_1 = [int(cmd_arg_1)]
                self.store.setValues(0x6, int(cmd_arg_0), cmd_arg_1)
            elif cmd == 'write_dw':
                cmd_arg_1 = [float(cmd_arg_1)]
                builder = BinaryPayloadBuilder(byteorder=endian_format(), wordorder=endian_format())
                builder.add_32bit_float(cmd_arg_1[0])
                payload = builder.to_registers()
                self.store.setValues(0x16, int(cmd_arg_0), payload)
            elif cmd == 'info':
                c.print('''Vendor Name:''', self.identity.VendorName,
                        '''\nProduct Code:''', self.identity.ProductCode,
                        '''\nVendor Url:''', self.identity.VendorUrl,
                        '''\nProduct Name:''', self.identity.ProductName,
                        '''\nModel Name:''', self.identity.ModelName,
                        '''\nMajor Minor Revision:''', self.identity.MajorMinorRevision, style='white on green'
                    )
            elif cmd == 'get_c':
                if not queueM.empty():
                    c.print(queueM.get())
            elif cmd == 'get_hr':
                if not queueD.empty():
                    c.print(queueD.get())
            # atualização das coils
            value = self.store.getValues(0x01,0,int(count_coils))
            value = [ bool(x) for x in value ]
            queueM.put(value)
            queueM_logic.put(value)
            # atualização dos registradores
            value = self.store.getValues(0x03,0,int(count_holding_register))
            queueD.put(value)
            #queueD_logic.put(value)
            sleep(0.1)


class Title(Static):
    pass

class OptionGroup(Container):
    pass

class Message(Static):
    pass
class Message_2(Static):
    pass
ABOUT_TITLE = """[b yellow]About[/]"""
ABOUT = f"""
[b white]Vendor name:[/] [b i green]{vendor_name}[/]
[b white]Product code:[/] [b i green]{product_code}[/]
[b white]Vendor url:[/] [@click="app.open_link('{vendor_url}')"][b i green]{vendor_url}[/]
[b white]Product name:[/] [b i green]{product_name}[/]
[b white]Model name:[/] [b i green]{model_name}[/]
[b white]Major minor_revision:[/] [b i green]{major_minor_revision}[/]

[@click="app.open_link('https://github.com/AlexandreRibeiro28/modbus_server_app')"]Modbus Server GitHub Repository[/]
v1.0
"""


class Sidebar(Container):
    def compose(self) -> ComposeResult:
        yield Title("Modbus Server settings")
        with Horizontal(classes='buttons_sidebar'):
            yield Button("Edit", id="btn_edit",classes="btn_edit")
            yield Button("Save", id="btn_save_settings", classes="btn_save_settings")
        with Horizontal(classes="ip"):
            yield Static("IP Address:", classes="ip_address_label")
            yield Input(classes='ip_address_input', type='text', value=str(ip), id="ip_address", disabled=True)
        with Horizontal(classes="port"):
            yield Static("Port:", classes="port_label")
            yield Input(classes='port_input', type='text', value=str(port), id="port", disabled=True)
        with Horizontal(classes="watch_window_size"):
            yield Static("Watch window size:", classes="watch_window_size_label")
            yield Input(classes='watch_window_size_input', type='integer' , value=str(watchTableSize), id="watch_window_size_input", disabled=True)
        with Horizontal(classes="coils_quantity"):
            yield Static("Coils quantity:", classes="coils_quantity_label")
            yield Input(classes='coils_quantity_input', type='integer' , value=str(count_coils), id="coils_quantity_input", disabled=True)
        with Horizontal(classes="registers_quantity"):
            yield Static("Registers quantity:", classes="registers_quantity_label")
            yield Input(classes='registers_quantity_input', type='integer' , value=str(count_holding_register), id="registers_quantity_input", disabled=True)
        yield OptionGroup(Message_2(ABOUT_TITLE),Message(ABOUT))

    @on(Button.Pressed, "#btn_edit")
    def edit_settings(self):
        self.query_one("#ip_address", Input).disabled = False
        self.query_one("#port", Input).disabled = False
        self.query_one("#watch_window_size_input", Input).disabled = False
        self.query_one("#coils_quantity_input", Input).disabled = False
        self.query_one("#registers_quantity_input", Input).disabled = False
    
    @on(Button.Pressed, "#btn_save_settings")
    def save_settings(self):
        with open(abs_file_path, 'r') as file:
            doc = yaml.safe_load(file)
        doc['identification']['ip_address'] = str(self.query_one("#ip_address", Input).value)
        doc['identification']['port'] = int(self.query_one("#port", Input).value)
        doc['data_block']['watch_window_size'] = int(self.query_one("#watch_window_size_input", Input).value)
        doc['data_block']['coils']['qty'] = int(self.query_one("#coils_quantity_input", Input).value)
        doc['data_block']['holding_registers']['qty'] = int(self.query_one("#registers_quantity_input", Input).value)

        with open(abs_file_path, 'w') as f:
            yaml.dump(doc, f)
        self.query_one("#ip_address", Input).disabled = True
        self.query_one("#port", Input).disabled = True
        self.query_one("#watch_window_size_input", Input).disabled = True
        self.query_one("#coils_quantity_input", Input).disabled = True
        self.query_one("#registers_quantity_input", Input).disabled = True
        queueMessageBetweenScreens.put("[b green]Saved with success. Application must be restarted to changes take effect.[/]")
FORMAT = """ 
Bin
Decimal
Hexadecimal
""".splitlines()

LINES = """ 
Word [Signed]
Double Word [Signed]
Bit
""".splitlines()

class ModbusServerApp(App):
    global watchTableSize
    global str_comments
    global comment_focused
    global modbus_server
    global server_is_running
    server_is_running = False
    comment_focused = ""
    str_comments = []
    BLANK = 'Word [Signed]'
    AUTO_FOCUS = "#device_addr_00"
    TITLE = 'Modbus Server'
    CSS_PATH = rel_path_css
    BINDINGS = [
        # Atalho, action, mensagem no footer
        ('t', 'change_theme()', 'Change Theme'),
        ('q', 'exit()', 'Close Application'),
        ('ctrl+s', 'save()', 'Save WatchWindow'),
        ('ctrl+l', 'load()', 'Load WatchWindow'),
        ('ctrl+o', 'toggle_sidebar()', 'Settings')
    ]
    def action_toggle_sidebar(self) -> None:
        #self.query_one(Sidebar).toggle_class("-hidden")
        sidebar = self.query_one(Sidebar)
        self.set_focus(None)
        if sidebar.has_class("-hidden"):
            sidebar.remove_class("-hidden")
        else:
            if sidebar.query("*:focus"):
                self.screen.set_focus(None)
            sidebar.add_class("-hidden")

    def action_change_theme(self):
        self.dark = not self.dark
    
    def action_open_link(self, link: str) -> None:
        self.app.bell()
        import webbrowser

        webbrowser.open(link)

    def action_exit(self):
        self.exit()

    def action_load(self):
        self.load_watch_window()


    def action_save(self):
        self.save_watch_window()


    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        yield Sidebar(classes="-hidden")
        with Horizontal(classes='label'):
            self.label = Label("Debug: ***", id='txt')
            yield self.label
            #yield Label("Debug: ***", id='txt2')
        with Horizontal(classes='buttons'):
            yield Button("Run ModbusServer ", id="start_server",classes="btn_start_server")
            yield Button("Close application", id="stop_app", classes="btn_stop_app")
            yield Button("Save WatchWindow", id="save", classes="btn_save")
            yield Button("Load WatchWindow", id="load", classes="btn_load")
            
        with ScrollableContainer(id='watch_window'):
            with Horizontal(classes="watch_window_colunms"):
                yield Label("Device address", classes="c0")
                yield Label("Prepared Value", classes="c1")
                yield Label("Current Value", classes="c2")
                yield Label("Display Format", classes="c3")
                yield Label("Data Type", classes="c4")
                yield Label("Comment", classes="c5")
            
            for n in range(watchTableSize):
                n = "{:02d}".format(n)
                with Horizontal(classes='watch_window_rows'):
                    yield Input(classes='device_addr', type='text', value="", id=f'device_addr_{n}', valid_empty=True,validators=[CheckInputAddress(),])
                    yield Input(classes='prepared_value', type='text', value="", id=f'prepared_value_{n}', valid_empty=True, disabled=False)
                    yield Input(value="", classes='current_value', id=f'current_value_{n}',disabled=True)
                    yield Select(((line, line) for line in FORMAT), classes=f'display_format', id=f'display_format_{n}', prompt='Select display format',allow_blank=False)
                    #yield Input(value="", classes='data_type', id=f'data_type_{n}',disabled=True)
                    yield Select(((line, line) for line in LINES), classes=f'data_type', id=f'data_type_{n}', prompt='Select data type',allow_blank=False)
                    yield Input(classes='comment', type='text', id=f'comment_{n}')


    def on_mount(self) -> None:
        global modbus_server
        global server_is_running
        global ip
        global port
        modbus_server = ModbusServerUpdate(ip= ip, port= port)
        self.run_worker(modbus_server.start_modbus_server(), exclusive=True)
        server_is_running = True
        self.query_one('#start_server', Button).label = "ModbusServer running"
        self.query_one('#start_server', Button).variant = "success"
        self.query_one('#start_server', Button)._update_styles

        thread3 = Thread(target=self.update_watch_window, args=(queueM, queueD,))
        thread3.daemon = True
        thread3.start()

        thread2 = Thread(target=self.update_logic, args=(queueM_logic, queueD_logic,))
        thread2.daemon = True
        thread2.start()

        self.query_one('#txt', Label).update(f"[green b]Modbus server started with IP address {ip} at port {port}[/]")
        self.query_one('#txt', Label).styles.opacity = 1.0
        self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=3.0)   

    
    def update_logic(self, queueM_logic, queueD_logic):
        global server_is_running
        global M
        global D
        sleep(1)
        while server_is_running:
            
            M = [False]*count_coils
            D = [0]*count_holding_register
            if not queueM_logic.empty():
                coils = queueM_logic.get()
                for n in range(count_coils):
                    M[n] = coils[n]
            if not queueD_logic.empty():
                registers = queueD_logic.get()
                for n in range(count_holding_register):
                    D[n] = registers[n]
            
            exec(logic_txt)
            if not queueM_logic.empty():
                coils = queueM_logic.get()
                m = ""
                for n in range(count_coils):
                    if M[n] != coils[n]:
                        if M[n] == True:
                            m = "1"
                        elif M[n] == False:
                            m = "0"
                        cmd = ['write_c', str(n), m]
                        queueCmdModbus.put(cmd)
            if not queueD_logic.empty():
                registers = queueD_logic.get()
                d = ""
                for n in range(count_holding_register):
                    if D[n] != registers[n]:
                        d = str(D[n])
                        cmd = ['write_hr', str(n), d]
                        queueCmdModbus.put(cmd)

            
            sleep(0.05)  

    def update_watch_window(self, queueM, queueD):
        global str_comments
        global comment_focused
        global server_is_running
        cs = Console()
        sleep(1)
        while server_is_running:
            if not queueMessageBetweenScreens.empty():
                self.query_one('#txt', Label).update(queueMessageBetweenScreens.get())
                self.query_one('#txt', Label).styles.opacity = 1.0
                self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)
            if not queueM.empty():
                values_coils = queueM.get()

            if not queueD.empty():
                values_holding_registers = queueD.get()       
            
            with queueM.mutex:
                queueM.queue.clear()
            with queueD.mutex:
                queueD.queue.clear()
            
            for n in range(watchTableSize):
                m = "{:02d}".format(n)
                addr_value = self.query_one(f"#device_addr_{m}", Input).value
                    
                if len(self.query_one(f"#device_addr_{m}", Input).value) >= 2:
                    if ( (addr_value[0] == "D") and ( addr_value[1:].isdecimal() ) ):
                        if int(self.query_one(f"#device_addr_{m}", Input).value[1:]) < count_holding_register:
                            if self.query_one(f"#data_type_{m}", Select).value == " " or self.query_one(f"#data_type_{m}", Select).value == "Bit":
                                self.query_one(f"#data_type_{m}", Select).value = "Word [Signed]"
                            
                            if self.query_one(f"#display_format_{m}", Select).value == " ":
                                self.query_one(f"#display_format_{m}", Select).value = "Decimal"                        
                            
                            if str(self.query_one(f"#data_type_{m}", Select).value) == "Double Word [Signed]":
                                decoder = BinaryPayloadDecoder.fromRegisters([values_holding_registers[int(self.query_one(f"#device_addr_{m}", Input).value[1:])], values_holding_registers[int(self.query_one(f"#device_addr_{m}", Input).value[1:]) + 1]], byteorder=endian_format(), wordorder=endian_format())
                                converted_value = str(round(decoder.decode_32bit_float(), 4))

                                if converted_value == "0.0":
                                    decoder = BinaryPayloadDecoder.fromRegisters([values_holding_registers[int(self.query_one(f"#device_addr_{m}", Input).value[1:])], values_holding_registers[int(self.query_one(f"#device_addr_{m}", Input).value[1:]) + 1]], byteorder=endian_format(), wordorder=endian_format())
                                    converted_value = str(decoder.decode_16bit_int())
                                else:
                                    decoder = BinaryPayloadDecoder.fromRegisters([values_holding_registers[int(self.query_one(f"#device_addr_{m}", Input).value[1:])], values_holding_registers[int(self.query_one(f"#device_addr_{m}", Input).value[1:]) + 1]], byteorder=endian_format(), wordorder=endian_format())
                                    converted_value = round(decoder.decode_32bit_float(),4)
                                    dec, whole = math.modf(converted_value)
                                    if dec == 0:
                                        converted_value = str(int(converted_value))
                                    else:
                                        converted_value = str(converted_value)
                                #self.query_one('#txt', Label).update(str(type(self.query_one("#data_type_02", Select).value)))
                                if self.query_one(f"#display_format_{m}", Select).value == "Bin":
                                    if self.query_one(f"#current_value_{m}", Input).value.find(".") < 0:     # não possui ponto, não é float
                                        converted_value = str(bin(int(converted_value)))
                                        converted_value = converted_value[2:len(converted_value)].zfill(16)
                                        self.query_one(f"#current_value_{m}", Input).value = converted_value
                                    else:
                                        self.query_one(f"#display_format_{m}", Select).value = "Decimal"
                                        self.query_one('#txt', Label).update("[red b]Unable to format value to bin.[/]")
                                        self.query_one('#txt', Label).styles.opacity = 1.0
                                        self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)
                                        self.app.bell()
                                elif self.query_one(f"#display_format_{m}", Select).value == "Hexadecimal":
                                    if self.query_one(f"#current_value_{m}", Input).value.find(".") < 0:     # não possui ponto, não é float
                                        converted_value = str(hex(int(converted_value)))
                                        converted_value = converted_value[2:len(converted_value)].zfill(4)
                                        converted_value = "H" + converted_value.upper()
                                        self.query_one(f"#current_value_{m}", Input).value = converted_value
                                    else:
                                        self.query_one(f"#display_format_{m}", Select).value = "Decimal"
                                        self.query_one('#txt', Label).update("[red b]Unable to format value to hex.[/]")
                                        self.query_one('#txt', Label).styles.opacity = 1.0
                                        self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)
                                        self.app.bell()
                                else:
                                    self.query_one(f"#current_value_{m}", Input).value = converted_value
                            else:
                                decoder = BinaryPayloadDecoder.fromRegisters([values_holding_registers[int(self.query_one(f"#device_addr_{m}", Input).value[1:])]], byteorder=endian_format(), wordorder=endian_format())
                                converted_value = str(decoder.decode_16bit_int())
                                if self.query_one(f"#display_format_{m}", Select).value == "Bin":
                                    converted_value = str(bin(int(converted_value)))
                                    converted_value = converted_value[2:len(converted_value)].zfill(16)
                                    self.query_one(f"#current_value_{m}", Input).value = converted_value
                                elif self.query_one(f"#display_format_{m}", Select).value == "Hexadecimal":
                                    converted_value = str(hex(int(converted_value)))
                                    converted_value = converted_value[2:len(converted_value)].zfill(4)
                                    converted_value = "H" + converted_value.upper()
                                    self.query_one(f"#current_value_{m}", Input).value = converted_value
                                else:
                                    self.query_one(f"#current_value_{m}", Input).value = converted_value
                        else:
                            self.query_one(f"#device_addr_{m}", Input).value = "D" + str(count_holding_register - 1)
                            self.query_one('#txt', Label).update("[red b]Address out of range.[/]")
                            self.query_one('#txt', Label).styles.opacity = 1.0
                            self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)
                            self.app.bell()
                    elif ( ( addr_value[0] == "M") and ( addr_value[1:].isdecimal() ) ):
                        if int(self.query_one(f"#device_addr_{m}", Input).value[1:]) < count_coils:
                            self.query_one(f"#display_format_{m}", Select).value = "Bin"
                            self.query_one(f"#data_type_{m}", Select).value = "Bit"
                            self.query_one(f"#current_value_{m}", Input).value = str(values_coils[int(self.query_one(f"#device_addr_{m}", Input).value[1:])])
                        else:
                            self.query_one(f"#device_addr_{m}", Input).value = "M" +  str(count_coils - 1)
                            self.query_one('#txt', Label).update("[red b]Address out of range.[/]")
                            self.query_one('#txt', Label).styles.opacity = 1.0
                            self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)
                            self.app.bell()
                    if str_comments:
                        for i in str_comments:
                            if i[0] == self.query_one(f"#device_addr_{m}", Input).value:
                                if comment_focused != f"comment_{m}":
                                    self.query_one(f"#comment_{m}", Input).value = i[1]
                else:
                    self.query_one(f"#current_value_{m}", Input).value = ""
                    self.query_one(f"#comment_{m}", Input).value = ""
            sleep(0.05)


    @on(events.DescendantFocus)
    def get_focused(self, event: events.DescendantFocus):
        global comment_focused
        comment_focused = event.widget.id


    @on(events.Click)
    def clear_message_on_event(self, event: events.Click):
        self.query_one('#txt', Label).update("")


    def clear_message(self):
        self.query_one('#txt', Label).update("")
        

    @on(Input.Submitted)
    def input_addr(self, event: Input.Submitted):
        global str_comments
        if event.input.id[:-3] == "prepared_value":
            value = event.input.value       # valor que foi imputado
            if value != "":
                input_row = event.input.id[len(event.input.id) - 2:]
                if self.query_one(f"#device_addr_{input_row}", Input).value != "":
                    addr = self.query_one(f"#device_addr_{input_row}", Input).value[1:]
                    if self.query_one(f"#device_addr_{input_row}", Input).value[0] == "D":
                        if int(self.query_one(f"#device_addr_{input_row}", Input).value[1:]) < count_holding_register:
                            if value.find(".") < 0:     # não possui ponto, não é float
                                if int(value) > 32000 or int(value) < 0:
                                    cmd = ['write_dw', addr, value]
                                else:
                                    cmd = ['write_hr', addr, value]
                            else:
                                cmd = ['write_dw', addr, value]
                            queueCmdModbus.put(cmd)
                        else:
                            self.query_one(f"#device_addr_{input_row}", Input).value = "D" +  str(count_holding_register - 1)
                            self.query_one('#txt', Label).update("[red b]Address out of range.[/]")
                            self.query_one('#txt', Label).styles.opacity = 1.0
                            self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)
                            self.app.bell()
                        self.clear_message()
                    elif self.query_one(f"#device_addr_{input_row}", Input).value[0] == "M":
                        if int(self.query_one(f"#device_addr_{input_row}", Input).value[1:]) < count_coils:
                            if value == "0" or value == "1":
                                cmd = ['write_c', addr, event.input.value]
                                queueCmdModbus.put(cmd)
                                self.clear_message()
                            else:
                                self.query_one('#txt', Label).update("[red b]Wrong value! Prepared value must be 1 or 0 for coils.[/]")
                                self.query_one('#txt', Label).styles.opacity = 1.0
                                self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)
                                self.app.bell()
                        else:
                            self.query_one(f"#device_addr_{input_row}", Input).value = "M" +  str(count_coils - 1)
                            self.query_one('#txt', Label).update("[red b]Address out of range.[/]")
                            self.query_one('#txt', Label).styles.opacity = 1.0
                            self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)
                            self.app.bell()
                else:
                    self.query_one('#txt', Label).update("[yellow b]Insert a valid device address.[/]")
                    self.query_one('#txt', Label).styles.opacity = 1.0
                    self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)
                    self.query_one('#txt', Label).styles.opacity = 1.0
                    self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)
                    self.app.bell()
                event.input.clear()
        elif event.input.id[:-3] == "comment":
            input_row = event.input.id[len(event.input.id) - 2:]
            if self.query_one(f"#device_addr_{input_row}", Input).value != "":
                input_row = event.input.id[len(event.input.id) - 2:]
                comment_match = False
                if not str_comments:            
                    str_comments.append([self.query_one(f"#device_addr_{input_row}", Input).value, event.input.value])
                else:
                    memory_addr = [i[0] for i in str_comments]
                    for n in range(len(memory_addr)):
                        if memory_addr[n] == self.query_one(f"#device_addr_{input_row}", Input).value:
                            str_comments[n] = [self.query_one(f"#device_addr_{input_row}", Input).value, event.input.value]
                            comment_match = True
                    if comment_match == False:
                        str_comments.append([self.query_one(f"#device_addr_{input_row}", Input).value, event.input.value])


    @on(Button.Pressed, "#load")
    def load_watch_window(self):
        global str_comments
        with open(rel_path_csv, 'r') as f:
            reader = csv.reader(f, delimiter=";")
            data = list(reader)
        for n in range(len(data)):
            if n >= watchTableSize:
                break
            m = "{:02d}".format(n)
            watch_window_row = data[n]
            if watch_window_row[0] != '':
                if str(watch_window_row[0])[0] == "D":
                    addr = str(watch_window_row[0])[1:len(str(watch_window_row[0]))]
                    value = watch_window_row[2]
                    if value.find(".") < 0:     # não possui ponto, não é float
                        if int(value) > 32000 or int(value) < 0:
                            cmd = ['write_dw', addr, value]
                        else:
                            cmd = ['write_hr', addr, value]
                    else:
                        cmd = ['write_dw', addr, value]
                    queueCmdModbus.put(cmd)
                elif str(watch_window_row[0])[0] == "M":
                    addr = str(watch_window_row[0])[1:len(str(watch_window_row[0]))]
                    value = watch_window_row[2]
                    if value == "True":
                        value = "1"
                    elif value == "False":
                        value = "0"
                    cmd = ['write_c', addr, value]
                    queueCmdModbus.put(cmd)

                comment_match = False
                if not str_comments:    # lista de comentários vazia           
                    str_comments.append([str(watch_window_row[0]), str(watch_window_row[5])])
                else:   # lista de comentários preenchida
                    memory_addr = [i[0] for i in str_comments]
                    for k in range(len(memory_addr)):   # procura pelo endereço dentro da lista de comentários
                        if str(memory_addr[k]) == str(watch_window_row[0]):
                            str_comments[k] = [str(watch_window_row[0]), str(watch_window_row[5])]
                            comment_match = True
                    if comment_match == False:
                        str_comments.append([str(watch_window_row[0]), str(watch_window_row[5])])
                
            self.query_one(f"#device_addr_{m}", Input).value = str(watch_window_row[0]) 
            self.query_one(f"#display_format_{m}", Select).value = str(watch_window_row[3])
            self.query_one(f"#data_type_{m}", Select).value = str(watch_window_row[4])
        
        self.query_one('#txt', Label).update("[green b]Loaded with success.[/]")
        self.query_one('#txt', Label).styles.opacity = 1.0
        self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)
        

    @on(Button.Pressed, "#save")
    def save_watch_window(self):
        watch_window = [['']*6]*watchTableSize
        for n in range(watchTableSize):
            m = "{:02d}".format(n)
            current_value = self.query_one(f"#current_value_{m}", Input).value
            if str(self.query_one(f"#data_type_{m}", Select).value) == "Word [Signed]" or str(self.query_one(f"#data_type_{m}", Select).value) == "Double Word [Signed]":
                if self.query_one(f"#display_format_{m}", Select).value == "Bin":            
                    current_value = str(int(self.query_one(f"#current_value_{m}", Input).value, 2))
                if self.query_one(f"#display_format_{m}", Select).value == "Hexadecimal":            
                    current_value = str(int(self.query_one(f"#current_value_{m}", Input).value[1:len(self.query_one(f"#current_value_{m}", Input).value)], 16))

            watch_window[n] =   [self.query_one(f"#device_addr_{m}", Input).value,
                                self.query_one(f"#prepared_value_{m}", Input).value,
                                current_value,
                                self.query_one(f"#display_format_{m}", Select).value,
                                self.query_one(f"#data_type_{m}", Select).value,
                                self.query_one(f"#comment_{m}", Input).value,
                                ]
        try:
            np.savetxt(rel_path_csv, watch_window, delimiter=";", fmt='%s')
            self.query_one('#txt', Label).update(f"[green b]Saved with success at[/] [white b]{rel_path_csv}.[/]")
            self.query_one('#txt', Label).styles.opacity = 1.0
            self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)
        except:
            self.query_one('#txt', Label).update(f"[red b]Unable to save at[/] [white b]{rel_path_csv}.[/]")
            self.query_one('#txt', Label).styles.opacity = 1.0
            self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)

    @on(Button.Pressed, "#stop_app")
    def stop_app(self):
        global server_is_running
        server_is_running = False
        sleep(0.3)
        self.exit()

    @on(Button.Pressed, "#start_server")
    def start_modbus_server(self, event: Button.Pressed):
        global modbus_server
        global server_is_running
        if server_is_running == True:   
            self.workers.cancel_all() 
            self.run_worker(ServerAsyncStop(), exclusive=True)
            server_is_running = False
            self.query_one('#start_server', Button).label = "ModbusServer stopped"
            self.query_one('#start_server', Button).variant = "error"
            self.query_one('#start_server', Button)._update_styles
            for n in range(watchTableSize):
                m = "{:02d}".format(n)
                self.query_one(f"#device_addr_{m}", Input).disabled = True
                self.query_one(f"#prepared_value_{m}", Input).disabled = True
            self.query_one('#txt', Label).update(f"[yellow b]Modbus server stopped[/]")
            self.query_one('#txt', Label).styles.opacity = 1.0
            self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)
        else:
            self.run_worker(modbus_server.start_modbus_server(), exclusive=True)
            self.query_one('#start_server', Button).label = "ModbusServer running"
            self.query_one('#start_server', Button).variant = "success"
            self.query_one('#start_server', Button)._update_styles
        
            server_is_running = True
            thread3 = Thread(target=self.update_watch_window, args=(queueM, queueD,))
            thread3.daemon = True
            thread3.start()

            thread2 = Thread(target=self.update_logic, args=(queueM_logic, queueD_logic,))
            thread2.daemon = True
            thread2.start()
            sleep(0.5)
            for n in range(watchTableSize):
                m = "{:02d}".format(n)
                self.query_one(f"#device_addr_{m}", Input).disabled = False
                self.query_one(f"#prepared_value_{m}", Input).disabled = False
            self.query_one('#txt', Label).update(f"[green b]Modbus server started with IP address {ip} at port {port}[/]")
            self.query_one('#txt', Label).styles.opacity = 1.0
            self.query_one('#txt', Label).styles.animate("opacity", value=0.0, duration=2.0)


class CheckInputAddress(Validator):  
    def validate(self, value: str) -> ValidationResult:
        if self.check_addr(value):
            return self.success()
        else:
            return self.failure("Invalid value")

    @staticmethod
    def check_addr(value: str) -> bool:
        if ( ( (value[0] == "D") or (value[0] == "M") ) and ( value[1:].isdecimal() ) ):
            if int(value[1:]) < count_holding_register and value[0] == "D":
                return True
            elif int(value[1:]) < count_coils and value[0] == "M":
                return True
        else:
            return False
           

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    ModbusServerApp().run()
