#!/usr/bin/env python3
import PySimpleGUI as sg
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from uese.core.universal_scanner import UniversalScanner
from uese.core.patch_engine import PatchEngine
from uese.core.profile_manager import ProfileManager

sg.theme('DarkBlue3')

def create_scanner_tab():
    layout = [
        [sg.Text('UESE Scanner - Diff-based Value Detection', font='Any 16 bold')],
        [sg.HorizontalSeparator()],
        [sg.Text('Save A:'), sg.Input(key='-SAVE_A-', size=(50,1)), sg.FileBrowse()],
        [sg.Text('Save B:'), sg.Input(key='-SAVE_B-', size=(50,1)), sg.FileBrowse()],
        [sg.Text('Save C:'), sg.Input(key='-SAVE_C-', size=(50,1)), sg.FileBrowse()],
        [sg.HorizontalSeparator()],
        [sg.Text('Value in A:'), sg.Input(key='-VAL_A-', size=(15,1)),
         sg.Text('Value in B:'), sg.Input(key='-VAL_B-', size=(15,1)),
         sg.Text('Value in C:'), sg.Input(key='-VAL_C-', size=(15,1))],
        [sg.Text('Width:'), sg.Combo([2, 4], default_value=4, key='-WIDTH-', size=(5,1)),
         sg.Text('bytes'), sg.Push(), sg.Button('SCAN', size=(15,1), button_color=('white', 'green'))],
        [sg.HorizontalSeparator()],
        [sg.Text('Results:', font='Any 12 bold')],
        [sg.Table(
            values=[],
            headings=['#', 'Offset (hex)', 'Offset (dec)', 'Score', 'Values'],
            key='-RESULTS-',
            auto_size_columns=False,
            col_widths=[3, 12, 12, 8, 20],
            num_rows=15,
            enable_events=True,
            select_mode=sg.TABLE_SELECT_MODE_BROWSE
        )],
        [sg.Text('', key='-SCAN_STATUS-', text_color='yellow')]
    ]
    return sg.Tab('Scanner', layout)

def create_editor_tab():
    layout = [
        [sg.Text('UESE Editor - Patch Save Files', font='Any 16 bold')],
        [sg.HorizontalSeparator()],
        [sg.Text('Save File:'), sg.Input(key='-PATCH_FILE-', size=(50,1)), sg.FileBrowse()],
        [sg.Text('Offset:'), sg.Input(key='-PATCH_OFFSET-', size=(15,1)),
         sg.Text('(hex or decimal, e.g. 0x1f2a or 8234)')],
        [sg.Text('New Value:'), sg.Input(key='-PATCH_VALUE-', size=(15,1))],
        [sg.Text('Width:'), sg.Combo([2, 4], default_value=4, key='-PATCH_WIDTH-', size=(5,1)), sg.Text('bytes')],
        [sg.Checkbox('Create backup', default=True, key='-BACKUP-')],
        [sg.Button('PATCH', size=(15,1), button_color=('white', 'orange')),
         sg.Button('Clear', size=(10,1))],
        [sg.HorizontalSeparator()],
        [sg.Multiline(
            '',
            key='-PATCH_LOG-',
            size=(70, 15),
            disabled=True,
            autoscroll=True,
            text_color='lime',
            background_color='black'
        )],
        [sg.Text('Backups stored in: ~/.uese_backups/', font='Any 9', text_color='gray')]
    ]
    return sg.Tab('Editor', layout)

def create_profile_tab():
    pm = ProfileManager()
    profiles = pm.list_profiles()
    
    layout = [
        [sg.Text('Game Profiles', font='Any 16 bold')],
        [sg.HorizontalSeparator()],
        [sg.Text('Available Profiles:')],
        [sg.Listbox(profiles, size=(30, 10), key='-PROFILE_LIST-', enable_events=True)],
        [sg.Button('Load Profile'), sg.Button('Refresh')],
        [sg.HorizontalSeparator()],
        [sg.Multiline('', key='-PROFILE_INFO-', size=(60, 10), disabled=True)]
    ]
    return sg.Tab('Profiles', layout)

def main():
    layout = [
        [sg.TabGroup([
            [create_scanner_tab(),
             create_editor_tab(),
             create_profile_tab()]
        ])],
        [sg.StatusBar('Ready', key='-STATUS-', size=(70,1))]
    ]
    
    window = sg.Window(
        'UESE - Universal Epic Save Editor v1.0',
        layout,
        size=(900, 600),
        resizable=True,
        finalize=True
    )
    
    scanner = UniversalScanner()
    patcher = PatchEngine()
    
    while True:
        event, values = window.read()
        
        if event == sg.WIN_CLOSED:
            break
        
        elif event == 'SCAN':
            try:
                saves = [Path(values['-SAVE_A-']), Path(values['-SAVE_B-']), Path(values['-SAVE_C-'])]
                vals = [int(values['-VAL_A-']), int(values['-VAL_B-']), int(values['-VAL_C-'])]
                width = int(values['-WIDTH-'])
                
                for s in saves:
                    if not s.exists():
                        sg.popup_error(f'File not found: {s}')
                        continue
                
                window['-SCAN_STATUS-'].update('Scanning...', text_color='yellow')
                window.refresh()
                
                candidates = scanner.scan_saves(saves[0], saves[1], saves[2], tuple(vals), width)
                
                if not candidates:
                    window['-SCAN_STATUS-'].update('No candidates found!', text_color='red')
                    window['-RESULTS-'].update([])
                else:
                    table_data = [
                        [i+1, f'{c.offset:#010x}', c.offset, c.score, str(c.values)]
                        for i, c in enumerate(candidates[:50])
                    ]
                    window['-RESULTS-'].update(table_data)
                    window['-SCAN_STATUS-'].update(f'Found {len(candidates)} candidates!', text_color='lime')
                    window['-STATUS-'].update(f'Scan complete: {len(candidates)} results')
            
            except Exception as e:
                sg.popup_error(f'Scan error: {e}')
                window['-SCAN_STATUS-'].update(f'Error: {e}', text_color='red')
        
        elif event == '-RESULTS-':
            if values['-RESULTS-']:
                selected_row = values['-RESULTS-'][0]
                table_data = window['-RESULTS-'].get()
                if table_data and selected_row < len(table_data):
                    row = table_data[selected_row]
                    window['-PATCH_OFFSET-'].update(row[1])
                    window['-STATUS-'].update(f'Selected offset {row[1]} - switch to Editor tab to patch')
        
        elif event == 'PATCH':
            try:
                save_path = Path(values['-PATCH_FILE-'])
                if not save_path.exists():
                    sg.popup_error(f'File not found: {save_path}')
                    continue
                
                offset_str = values['-PATCH_OFFSET-']
                offset = int(offset_str, 16) if offset_str.startswith('0x') else int(offset_str)
                value = int(values['-PATCH_VALUE-'])
                width = int(values['-PATCH_WIDTH-'])
                backup = values['-BACKUP-']
                
                log = f'Patching {save_path.name}...\n'
                log += f'Offset: {offset:#x}\n'
                log += f'New value: {value}\n'
                log += f'Width: {width} bytes\n'
                
                if patcher.patch_value(save_path, offset, width, value, backup):
                    log += '\n✅ PATCH SUCCESS!\n'
                    if backup:
                        log += f'📦 Backup created in ~/.uese_backups/\n'
                    
                    if patcher.verify_patch(save_path, offset, value, width):
                        log += '✅ Verification OK!\n'
                    
                    window['-PATCH_LOG-'].update(window['-PATCH_LOG-'].get() + log)
                    window['-STATUS-'].update('Patch applied successfully!')
                    sg.popup_ok('Patch successful! Load the save in your game.', title='Success')
                
            except Exception as e:
                error_log = f'\n❌ ERROR: {e}\n'
                window['-PATCH_LOG-'].update(window['-PATCH_LOG-'].get() + error_log)
                sg.popup_error(f'Patch error: {e}')
        
        elif event == 'Clear':
            window['-PATCH_LOG-'].update('')
        
        elif event == 'Refresh':
            pm = ProfileManager()
            profiles = pm.list_profiles()
            window['-PROFILE_LIST-'].update(profiles)
    
    window.close()

if __name__ == '__main__':
    main()
