STYLE = r"""
QMainWindow, QWidget { background: transparent; color: #f2f2f2; font-family: 'Segoe UI'; }
QWidget#glassShell { background: rgba(8, 10, 12, 172); border: 1px solid rgba(235, 240, 255, 42); border-radius: 0px; }
QFrame#settingsDrawer { background: rgba(7, 9, 12, 238); border-right: 1px solid rgba(235, 240, 255, 45); }
QWidget#contentHeader { background: rgba(5, 6, 8, 80); }
QFrame#previewDrawer { background: rgba(7, 9, 12, 245); border-left: 1px solid rgba(235, 240, 255, 45); }
QLabel#previewTitle { color: #f1f4f8; font-size: 16px; font-weight: 600; }
QLabel#previewPath { color: #aeb7c5; font-size: 11px; padding: 3px 0; }
QToolButton#previewButton { background: rgba(255, 255, 255, 13); border: 1px solid rgba(255, 255, 255, 35); border-radius: 15px; min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; padding: 0; color: #dce2eb; font-size: 22px; }
QToolButton#previewButton:hover { background: rgba(255, 255, 255, 38); border-color: rgba(255, 255, 255, 100); }
QListWidget#previewList { background: rgba(255, 255, 255, 7); border: 1px solid rgba(235, 240, 255, 28); color: #d9dee6; padding: 4px; }
QListWidget#previewList::item { padding: 7px 6px; border-radius: 5px; }
QListWidget#previewList::item:selected { background: rgba(210, 220, 235, 32); color: #ffffff; }
QTextEdit#previewContent { background: rgba(3, 4, 6, 210); border: 1px solid rgba(235, 240, 255, 28); color: #e6ebf2; padding: 9px; font-family: Consolas, 'Microsoft YaHei'; font-size: 12px; }
QTextEdit#previewContent QScrollBar:vertical { width: 10px; background: rgba(255, 255, 255, 10); margin: 0; }
QTextEdit#previewContent QScrollBar::handle:vertical { background: rgba(220, 226, 236, 145); border-radius: 5px; min-height: 28px; }
QTextEdit#previewContent QScrollBar::handle:vertical:hover { background: rgba(245, 248, 255, 205); }
QTextEdit#previewContent QScrollBar::add-line:vertical, QTextEdit#previewContent QScrollBar::sub-line:vertical { height: 0; }
QTextEdit#previewContent QScrollBar::add-page:vertical, QTextEdit#previewContent QScrollBar::sub-page:vertical { background: transparent; }
QLabel#drawerTitle { color: #f1f4f8; font-size: 16px; font-weight: 600; }
QLabel#drawerMeta, QLabel#drawerStatus { color: #858c96; font-size: 11px; }
QToolButton#appIcon { background: transparent; border: 0; padding: 0; }
QToolButton#drawerClose { background: transparent; border: 0; color: #8e96a1; font-size: 22px; padding: 0; min-width: 24px; }
QToolButton#drawerClose:hover { color: #ffffff; }
QListWidget#historyList { background: rgba(255, 255, 255, 7); border: 1px solid rgba(235, 240, 255, 28); color: #d9dee6; padding: 5px; }
QListWidget#historyList::item { padding: 9px 8px; border-radius: 7px; }
QListWidget#historyList::item:selected { background: rgba(210, 220, 235, 32); color: #ffffff; }
QPushButton#drawerAction { padding: 7px 10px; min-width: 0; }
QTextEdit#conversation { background: transparent; border: 0; color: #eeeeee; padding: 28px 10px; font-size: 15px; selection-background-color: rgba(160, 170, 190, 90); }
QTextEdit#conversation QScrollBar:vertical { width: 11px; background: rgba(255, 255, 255, 8); margin: 3px 0; border-radius: 5px; }
QTextEdit#conversation QScrollBar::handle:vertical { background: rgba(220, 226, 236, 150); border-radius: 5px; min-height: 34px; }
QTextEdit#conversation QScrollBar::handle:vertical:hover { background: rgba(248, 250, 255, 220); }
QTextEdit#conversation QScrollBar::add-line:vertical, QTextEdit#conversation QScrollBar::sub-line:vertical { height: 0; }
QTextEdit#conversation QScrollBar::add-page:vertical, QTextEdit#conversation QScrollBar::sub-page:vertical { background: transparent; }
QFrame#composer { background: rgba(3, 4, 6, 185); border: 1px solid rgba(235, 240, 255, 58); border-radius: 17px; }
QLineEdit#prompt { background: transparent; border: 0; padding: 11px 5px; color: #f5f5f5; font-size: 15px; }
QLineEdit#prompt:focus { border-color: rgba(235, 240, 255, 115); }
QPushButton { background: rgba(35, 38, 44, 180); border: 1px solid rgba(235, 240, 255, 45); border-radius: 0px; color: #eeeeee; padding: 10px 15px; }
QPushButton:hover { background: rgba(85, 90, 100, 185); border-color: rgba(255, 255, 255, 110); }
QPushButton#windowButton { background: rgba(255, 255, 255, 16); border: 1px solid rgba(255, 255, 255, 28); border-radius: 0px; padding: 5px 9px; min-width: 28px; max-width: 58px; }
QPushButton#windowButton:checked { background: rgba(180, 190, 205, 70); border-color: rgba(255, 255, 255, 95); }
QPushButton#sendButton { background: rgba(245, 246, 248, 225); color: #0a0a0a; border-color: rgba(255, 255, 255, 200); min-width: 72px; }
QPushButton#sendButton[running="true"] { background: rgba(35, 38, 44, 220); color: #ffffff; border-color: rgba(255, 255, 255, 80); }
QPushButton#voiceButton { background: rgba(25, 28, 33, 170); border-radius: 0px; min-width: 36px; max-width: 36px; padding: 8px; font-size: 16px; }
QToolButton#voiceButton { background: rgba(35, 39, 46, 210); border: 1px solid rgba(255, 255, 255, 48); border-radius: 15px; min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; padding: 6px; }
QToolButton#voiceButton[listening="true"] { background: rgba(4, 5, 7, 235); border-color: rgba(255, 255, 255, 120); }
QToolButton#voiceButton:hover { background: rgba(100, 108, 122, 170); border-color: rgba(255, 255, 255, 120); }
QToolButton#voiceButton:disabled { background: rgba(35, 39, 46, 100); }
QToolButton#imageButton { background: rgba(35, 39, 46, 210); border: 1px solid rgba(255, 255, 255, 48); border-radius: 15px; min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; color: #dce2eb; font-size: 18px; }
QToolButton#imageButton:hover { background: rgba(100, 108, 122, 170); border-color: rgba(255, 255, 255, 120); }
QToolButton#imageButton:disabled { background: rgba(35, 39, 46, 100); }
QToolButton#sendButton { background: rgba(245, 246, 248, 230); color: #090a0c; border: 0; border-radius: 12px; min-width: 64px; min-height: 34px; padding: 0 13px; }
QToolButton#sendButton:hover { background: #ffffff; }
QToolButton#sendButton[running="true"] { background: rgba(48, 52, 60, 235); color: #ffffff; border: 1px solid rgba(255, 255, 255, 70); }
QPushButton#compactButton { padding: 7px 12px; border-radius: 10px; }
QPushButton#reasoningButton { background: rgba(255, 255, 255, 13); border: 1px solid rgba(255, 255, 255, 35); border-radius: 10px; color: #dce2eb; padding: 7px 10px; }
QPushButton#reasoningButton:hover { background: rgba(255, 255, 255, 38); border-color: rgba(255, 255, 255, 100); }
QToolButton#settingsButton { background: rgba(255, 255, 255, 13); border: 1px solid rgba(255, 255, 255, 35); border-radius: 15px; min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; padding: 6px; }
QToolButton#settingsButton:hover { background: rgba(255, 255, 255, 38); border-color: rgba(255, 255, 255, 100); }
QLabel#appTitle { color: #ffffff; font-size: 17px; font-weight: 600; }
QLabel#statusTop, QLabel#aiLabel, QLabel#streamStatus { color: #898989; font-size: 12px; }
QLabel#progressLabel { color: #aeb7c5; font-size: 12px; padding: 2px 8px; }
QLabel#progressLabel[active="true"] { color: #d5dce7; }
QTextEdit#activity { background: transparent; border: 0; color: #888888; }
QComboBox#modelPicker { background: rgba(15, 17, 21, 180); border: 1px solid rgba(235, 240, 255, 45); border-radius: 0px; padding: 7px 12px; color: #cfcfcf; min-width: 180px; }
QComboBox#modelPicker QAbstractItemView { background: #181a1e; color: #eeeeee; selection-background-color: #40444d; }
QDialog { background: #0a0a0a; color: #eeeeee; }
QLabel#dialogTitle { color: #ffffff; font-size: 18px; font-weight: 600; }
QLabel#permissionSummary { background: rgba(255, 255, 255, 8); border: 1px solid rgba(235, 240, 255, 28); border-radius: 8px; color: #c8ced8; padding: 10px; }
QPushButton#permissionDeny, QPushButton#permissionAllow { border-radius: 8px; padding: 8px 18px; font-size: 14px; }
QPushButton#permissionDeny { background: rgba(70, 73, 80, 180); color: #f1f1f1; }
QPushButton#permissionAllow { background: rgba(235, 239, 246, 235); color: #111318; }
QPushButton#permissionDeny:hover { background: rgba(105, 109, 119, 220); }
QPushButton#permissionAllow:hover { background: #ffffff; }
QLabel#muted { color: #888888; }
QLineEdit#settingsField { background: #151515; border: 1px solid #303030; border-radius: 0px; padding: 9px; color: #eeeeee; }
QSizeGrip { width: 16px; height: 16px; background: rgba(220, 225, 235, 90); }
QScrollBar { width: 0px; height: 0px; background: transparent; }
QScrollBar::handle, QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page { width: 0px; height: 0px; background: transparent; }
"""
LIGHT_STYLE = STYLE
