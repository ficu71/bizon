#!/usr/bin/env python3
import PySimpleGUI as sg
from pathlib import Path
from uese.core.universal_scanner import UniversalScanner
from uese.core.patch_engine import PatchEngine

sg.theme('DarkBlue3')

layout_scan = [
    [sg.Text('UESE Scanner', font='Any 16 bold')],
    [sg.Text('Save A:'), sg.Input(key='SA', size=(40,1)), sg.FileBrowse()],
    [sg.Text('Save B:'), sg.Input(key='SB', size=(40,1)), sg.FileBrowse()],
    [sg.Text('Save C:'), sg.Input(key='SC', size=(40,1)), sg.FileBrowse()],
    [sg.Text('Val A:'), sg.In(key='VA',s=(8,1)), sg.T('B:'), sg.In(key='VB',s=(8,1)), sg.T('C:'), sg.In(key='VC',s=(8,1))],
    [sg.T('Width:'), sg.Combo([2,4], default_value=4, key='W'), sg.Button('SCAN', button_color=('white','green'))],
    [sg.Table(values=[], headings=['#','Offset','Score'], key='RES', num_rows=12, enable_events=True)],
    [sg.Text('', key='ST', text_color='yellow')]
]

layout_patch = [
    [sg.Text('UESE Patcher', font='Any 16 bold')],
    [sg.Text('File:'), sg.Input(key='F', size=(40,1)), sg.FileBrowse()],
    [sg.Text('Offset:'), sg.Input(key='O', size=(15,1)), sg.T('(hex or dec)')],
    [sg.Text('Value:'), sg.Input(key='V', size=(15,1))],
    [sg.Text('Width:'), sg.Combo([2,4], default_value=4, key='EW')],
    [sg.Button('PATCH', button_color=('white','orange'))],
    [sg.Multiline('', key='LOG', size=(60,10), disabled=True, autoscroll=True, background_color='black', text_color='lime')]
]

layout = [[sg.TabGroup([[sg.Tab('Scanner', layout_scan), sg.Tab('Patcher', layout_patch)]])]]

window = sg.Window('UESE v1.0', layout, size=(750,500), finalize=True)
scanner = UniversalScanner()
patcher = PatchEngine()

while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break
    
    elif event == 'SCAN':
        try:
            saves = [Path(values['SA']), Path(values['SB']), Path(values['SC'])]
            vals = (int(values['VA']), int(values['VB']), int(values['VC']))
            width = int(values['W'])
            window['ST'].update('Scanning...')
            window.refresh()
            candidates = scanner.scan_saves(saves[0], saves[1], saves[2], vals, width)
            data = [[i+1, f'{c.offset:#x}', c.score] for i,c in enumerate(candidates[:30])]
            window['RES'].update(data)
            window['ST'].update(f'Found {len(candidates)} candidates!', text_color='lime')
        except Exception as e:
            sg.popup_error(f'Error: {e}')
    
    elif event == 'RES':
        if values['RES']:
            sel = values['RES'][0]
            data = window['RES'].get()
            if data and sel < len(data):
                window['O'].update(data[sel][1])
    
    elif event == 'PATCH':
        try:
            save = Path(values['F'])
            off_str = values['O']
            off = int(off_str, 16) if off_str.startswith('0x') else int(off_str)
            val = int(values['V'])
            width = int(values['EW'])
            patcher.patch_value(save, off, width, val)
            log = f'Patched {save.name} at {off:#x} = {val}\n'
            window['LOG'].update(window['LOG'].get() + log)
            sg.popup_ok('Success!')
        except Exception as e:
            sg.popup_error(f'Error: {e}')

window.close()
