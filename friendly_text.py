"""Plain normal-flow status text; technical reports retain exact diagnostics."""
import re
from tkinter import StringVar


def friendly_status(value):
    text = str(value)
    for pattern, replacement in ((r'(?i)\bscrcpy(?:\.exe)?\b', 'phone screen service'),
                                 (r'(?i)\badb(?:\.exe)?\b', 'phone connection'),
                                 (r'(?i)\bUHID\b', 'compatibility mode'),
                                 (r'\bfile_push\b', 'File transfer'),
                                 (r'\bopen_url\b', 'Link'),
                                 (r'\bphone_folder\b', 'Phone files')):
        text = re.sub(pattern, replacement, text)
    return text


class FriendlyStatusVar(StringVar):
    def __init__(self, *args, **kwargs):
        if 'value' in kwargs:
            kwargs['value'] = friendly_status(kwargs['value'])
        super().__init__(*args, **kwargs)

    def set(self, value):
        return super().set(friendly_status(value))


def device_name(device):
    state = {'device': 'Ready', 'unauthorized': 'Approval needed', 'offline': 'Reconnecting'}.get(device.state, 'Unavailable')
    # Last four characters distinguish same-model devices without showing a raw
    # technical transport string or putting trusted-host details in normal UI.
    suffix = device.serial[-4:]
    return f'{device.model} · {state} · {suffix}'
