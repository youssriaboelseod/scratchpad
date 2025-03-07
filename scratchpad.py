""" Import the necessary modules for the program to work """
import sys
import os
import requests
import validators
import chardet
from chardet.universaldetector import UniversalDetector
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QAction,
                             QFileDialog, QMessageBox, QStatusBar, QDialog,
                             QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QIcon, QTextCursor, QTextDocument


""" Thread for handling file-related operations. """
class FileHandler(QThread):
    file_content_loaded = pyqtSignal(str, str)
    file_saved = pyqtSignal(bool)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
            """Read the content of the file with encoding detection and incremental loading."""
            detector = chardet.universaldetector.UniversalDetector()
            try:
                with open(self.file_path, 'rb') as file:
                    while chunk := file.read(1024):
                        detector.feed(chunk)
                        if detector.done:
                            break
                    detector.close()
                encoding = detector.result['encoding'] or 'utf-8'
                with open(self.file_path, 'r', encoding=encoding, errors='replace') as file:
                    content = ""
                    chunk_size = 1024 * 1024
                    while chunk := file.read(chunk_size):
                        content += chunk
                        self.file_content_loaded.emit(content, encoding)
                self.file_content_loaded.emit(content, encoding)
            except Exception as e:
                self.file_content_loaded.emit(f"Error reading file: {e}", '')

def load_icon(icon_name):
    """Utility function to load icons."""
    icon_path = os.path.join(os.path.dirname(__file__), icon_name)
    if getattr(sys, 'frozen', False):
        icon_path = os.path.join(sys._MEIPASS, icon_name)
    if os.path.exists(icon_path):
        return QIcon(icon_path)
    return None

def loadStyle():
    """Load CSS styles globally for the application."""
    user_css_path = os.path.join(os.path.expanduser("~"), "spstyle.css")
    stylesheet = None
    if os.path.exists(user_css_path):
        try:
            with open(user_css_path, 'r') as css_file:
                stylesheet = css_file.read()
            print(f"Loaded user CSS style from: {user_css_path}")
        except Exception as e:
            print(f"Error loading user CSS: {e}")
    else:
        css_file_path = os.path.join(os.path.dirname(__file__), 'style.css')
        if getattr(sys, 'frozen', False):
            css_file_path = os.path.join(sys._MEIPASS, 'style.css')
        try:
            with open(css_file_path, 'r') as css_file:
                stylesheet = css_file.read()
        except FileNotFoundError:
            print(f"Default CSS file not found: {css_file_path}")
    if stylesheet:
        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet)
        else:
            print("No QApplication instance found. Stylesheet not applied.")

class FindReplaceDialog(QDialog):
    """Dialog for Find and Replace functionality."""
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        self.setWindowTitle("Find and Replace")
        self.setWindowIcon(load_icon('scratchpad.png'))
        self.layout = QVBoxLayout(self)
        self.find_label = QLabel("Find:")
        self.find_input = QLineEdit(self)
        self.layout.addWidget(self.find_label)
        self.layout.addWidget(self.find_input)
        self.replace_label = QLabel("Replace with:")
        self.replace_input = QLineEdit(self)
        self.layout.addWidget(self.replace_label)
        self.layout.addWidget(self.replace_input)
        self.button_layout = QHBoxLayout()
        self.find_button = QPushButton("Find Next", self)
        self.replace_button = QPushButton("Replace", self)
        self.replace_all_button = QPushButton("Replace All", self)
        self.button_layout.addWidget(self.find_button)
        self.button_layout.addWidget(self.replace_button)
        self.button_layout.addWidget(self.replace_all_button)
        self.layout.addLayout(self.button_layout)
        self.find_button.clicked.connect(self.find_next)
        self.replace_button.clicked.connect(self.replace)
        self.replace_all_button.clicked.connect(self.replace_all)
        self.setLayout(self.layout)
        self.current_index = 0

    def find_next(self):
        """Find the next occurrence of the text."""
        text_to_find = self.find_input.text().strip()
        if text_to_find:
            options = QTextDocument.FindFlags()
            found = self.text_edit.find(text_to_find, options)
            if not found:
                QMessageBox.information(self, "Not Found", "No more occurrences found.")
        else:
            QMessageBox.warning(self, "Empty Search", "Please enter text to find.")

    def replace(self):
        """Replace the current occurrence."""
        text_to_find = self.find_input.text()
        text_to_replace = self.replace_input.text()
        if text_to_find and text_to_replace:
            content = self.text_edit.toPlainText()
            self.text_edit.setPlainText(content.replace(text_to_find, text_to_replace, 1))

    def replace_all(self):
        """Replace all occurrences."""
        text_to_find = self.find_input.text()
        text_to_replace = self.replace_input.text()
        if text_to_find and text_to_replace:
            content = self.text_edit.toPlainText()
            self.text_edit.setPlainText(content.replace(text_to_find, text_to_replace))


class ImportFromWebDialog(QDialog):
    """Dialog for importing content from the web using a URL."""
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        self.setWindowTitle("Import From Web")
        self.setWindowIcon(load_icon('scratchpad.png'))
        self.layout = QVBoxLayout(self)
        self.url_label = QLabel("Enter URL:")
        self.url_input = QLineEdit(self)
        self.layout.addWidget(self.url_label)
        self.layout.addWidget(self.url_input)
        self.fetch_button = QPushButton("Fetch", self)
        self.layout.addWidget(self.fetch_button)
        self.fetch_button.clicked.connect(self.fetch_from_web)
        self.setLayout(self.layout)

    def fetch_from_web(self):
        """Fetch the content from the provided URL and display it in the text editor."""
        url = self.url_input.text().strip()
        if self.is_valid_url(url):
            try:
                response = requests.get(url)
                response.raise_for_status()
                self.text_edit.setPlainText(response.text)
                self.accept()
            except requests.exceptions.RequestException as e:
                QMessageBox.critical(self, "Error", f"Failed to fetch content: {e}")
        else:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid HTTPS URL.")

    def is_valid_url(self, url):
        """Check if the provided URL is a valid HTTPS URL using validators library."""
        return validators.url(url) and url.startswith("https://")

class UnsavedWorkDialog(QDialog):
    """Dialog for warning about unsaved changes."""
    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle("Unsaved Changes")
        self.setWindowIcon(load_icon('scratchpad.png'))
        self.layout = QVBoxLayout(self)
        self.message_label = QLabel("You have unsaved changes. What would you like to do?")
        self.layout.addWidget(self.message_label)
        self.button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Changes", self)
        self.cancel_button = QPushButton("Cancel", self)
        self.discard_button = QPushButton("Discard Changes", self)
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.cancel_button)
        self.button_layout.addWidget(self.discard_button)
        self.layout.addLayout(self.button_layout)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.discard_button.clicked.connect(self.discard_changes)

        self.setLayout(self.layout)

    def discard_changes(self):
        """Handle discard changes action."""
        self.done(2)

class Scratchpad(QMainWindow):
    def __init__(self, file_to_open=None):
        super().__init__()
        self.current_file = file_to_open
        self.file_handler = None
        self.unsaved_changes = False
        self.initUI()
        if file_to_open:
            self.load_file_on_startup(file_to_open)

    def load_file_on_startup(self, file_path):
        """Load a file automatically on startup."""
        if os.path.exists(file_path):
            self.current_file = file_path
            self.file_handler = FileHandler(file_path)
            self.file_handler.file_content_loaded.connect(self.loadFileContent)
            self.file_handler.start()
        else:
            QMessageBox.critical(self, "Error", f"File does not exist: {file_path}")

    def closeEvent(self, event):
        if self.textEdit.document().isModified():
            dialog = UnsavedWorkDialog(self)
            result = dialog.exec_()
            if result == QDialog.Accepted:
                self.saveFile()
                event.accept()
            elif result == QDialog.Rejected:
                event.ignore()
            elif result == 2:
                event.accept()
        else:
            event.accept()

    def initUI(self):
        """Initialize the UI components."""
        self.setWindowTitle('Scratchpad - Unnamed')
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(load_icon('scratchpad.png'))
        self.textEdit = QTextEdit(self)
        self.setCentralWidget(self.textEdit)
        self.textEdit.setAcceptRichText(False)
        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)
        self.line = 1
        self.column = 1
        self.char_count = 0
        self.encoding = "UTF-8"
        self.textEdit.cursorPositionChanged.connect(self.updateStatusBar)
        self.createMenu()
        self.textEdit.textChanged.connect(self.on_text_changed)

    def on_text_changed(self):
        """Update the unsaved changes flag when text is modified."""
        self.unsaved_changes = True

    def createMenu(self):
        """Create the menu bar and connect actions."""
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        self.createFileActions(fileMenu)
        editMenu = menubar.addMenu('&Edit')
        self.createEditActions(editMenu)

    def createFileActions(self, menu):
        """Create file actions and add them to the given menu."""
        self.actions = {}
        newAction = QAction('New', self)
        newAction.setShortcut('Ctrl+N')
        newAction.triggered.connect(self.newFile)
        menu.addAction(newAction)
        self.actions['new'] = newAction
        openAction = QAction('Open...', self)
        openAction.setShortcut('Ctrl+O')
        openAction.triggered.connect(self.openFile)
        menu.addAction(openAction)
        self.actions['open'] = openAction
        saveAction = QAction('Save', self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.triggered.connect(self.saveFile)
        menu.addAction(saveAction)
        self.actions['save'] = saveAction
        saveAsAction = QAction('Save As...', self)
        saveAsAction.setShortcut('Ctrl+Shift+S')
        saveAsAction.triggered.connect(self.saveFileAs)
        menu.addAction(saveAsAction)
        self.actions['saveas'] = saveAsAction
        importFromWebAction = QAction('Import From Web', self)
        importFromWebAction.setShortcut('Ctrl+I')
        importFromWebAction.triggered.connect(self.importFromWeb)
        menu.addAction(importFromWebAction)
        self.actions['importfromweb'] = importFromWebAction
        exitAction = QAction('Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)
        menu.addAction(exitAction)
        self.actions['exit'] = exitAction

    def createEditActions(self, menu):
        """Create edit actions and add them to the given menu."""
        undoAction = QAction('Undo', self)
        undoAction.setShortcut('Ctrl+Z')
        undoAction.triggered.connect(self.textEdit.undo)
        menu.addAction(undoAction)
        self.actions['undo'] = undoAction
        redoAction = QAction('Redo', self)
        if sys.platform != 'darwin':
            redoAction.setShortcuts(['Ctrl+Y', 'Ctrl+Shift+Z'])
        else:
            redoAction.setShortcuts(['Ctrl+Shift+Z', 'Ctrl+Y'])
        redoAction.triggered.connect(self.textEdit.redo)
        menu.addAction(redoAction)
        self.actions['redo'] = redoAction
        cutAction = QAction('Cut', self)
        cutAction.setShortcut('Ctrl+X')
        cutAction.triggered.connect(self.textEdit.cut)
        menu.addAction(cutAction)
        self.actions['cut'] = cutAction
        copyAction = QAction('Copy', self)
        copyAction.setShortcut('Ctrl+C')
        copyAction.triggered.connect(self.textEdit.copy)
        menu.addAction(copyAction)
        self.actions['copy'] = copyAction
        pasteAction = QAction('Paste', self)
        pasteAction.setShortcut('Ctrl+V')
        pasteAction.triggered.connect(self.textEdit.paste)
        menu.addAction(pasteAction)
        self.actions['paste'] = pasteAction
        selectAllAction = QAction('Select All', self)
        selectAllAction.setShortcut('Ctrl+A')
        selectAllAction.triggered.connect(self.textEdit.selectAll)
        menu.addAction(selectAllAction)
        self.actions['selectall'] = selectAllAction
        findReplaceAction = QAction('Find and Replace...', self)
        findReplaceAction.triggered.connect(self.openFindReplaceDialog)
        findReplaceAction.setShortcut('Ctrl+F')
        menu.addAction(findReplaceAction)
        self.actions['findreplace'] = findReplaceAction

    def openFindReplaceDialog(self):
        """Open the find and replace dialog."""
        dialog = FindReplaceDialog(self.textEdit)
        dialog.exec_()

    def importFromWeb(self):
        """Open the dialog to import content from the web."""
        dialog = ImportFromWebDialog(self.textEdit)
        dialog.exec_()

    def newFile(self):
        """Create a new file."""
        self.current_file = None
        self.textEdit.clear()
        self.setWindowTitle('Scratchpad - Unnamed')

    def openFile(self):
        """Open a file for editing."""
        options = QFileDialog.Options()
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Text Files (*.txt);;All Files (*)", options=options)
            if file_name:
                self.current_file = file_name
                self.file_handler = FileHandler(file_name)
                self.file_handler.file_content_loaded.connect(self.loadFileContent)
                self.file_handler.start()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open file: {e}")

    def loadFileContent(self, content, encoding):
        """Load the content into the text edit."""
        if encoding:
            self.encoding = encoding
        if content.startswith("Error reading file"):
            QMessageBox.critical(self, "Error", content)
        else:
            self.textEdit.setPlainText(content)
            self.setWindowTitle(f'Scratchpad - {os.path.basename(self.current_file)}')

    def saveFile(self):
        """Save the current file."""
        content = self.textEdit.toPlainText()
        if self.encoding is None:
            self.encoding = 'utf-8'
        try:
            content.encode(self.encoding)
            if self.current_file:
                self.saveFileWithEncoding(content, self.encoding)
                self.unsaved_changes = False
                self.updateStatusBar(after_save=True)
            else:
                self.saveFileAs()
        except UnicodeEncodeError:
            self.promptForEncoding(content)

    def promptForEncoding(self, content):
        """Prompt the user for encoding if characters can't be saved in UTF-8."""
        encoding, ok = QInputDialog.getItem(self, "Choose Encoding", "Select Encoding", 
                                             ["UTF-8", "ISO-8859-1", "Windows-1252", "UTF-16"], 0, False)
        if ok:
            self.saveFileWithEncoding(content, encoding)
    
    def saveFileWithEncoding(self, content, encoding):
        """Save the file with the chosen encoding."""
        if self.current_file:
            try:
                with open(self.current_file, 'w', encoding=encoding) as file:
                    file.write(content)
                self.unsaved_changes = False
                self.updateStatusBar(after_save=True)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save file with encoding '{encoding}': {e}")


    def handleSaveFile(self, success):
        """Handle the result of the save operation."""
        if success:
            self.unsaved_changes = False
            self.updateStatusBar()
        else:
            QMessageBox.warning(self, "Error", "Failed to save file!")

    def saveFileAs(self):
        """Save the current file as a new file."""
        options = QFileDialog.Options()
        try:
            file_name, _ = QFileDialog.getSaveFileName(self, "Save File As", "", "Text Files (*.txt);;All Files (*)", options=options)
            if file_name:
                self.current_file = file_name
                self.saveFile()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save file: {e}")

    def updateStatusBar(self, after_save=False):
        """Update the status bar with line and column information."""
        cursor = self.textEdit.textCursor()
        self.line = cursor.blockNumber() + 1
        self.column = cursor.columnNumber() + 1
        self.char_count = len(self.textEdit.toPlainText())

        asterisk = ""
        if not after_save:
            asterisk = "*" if self.unsaved_changes else ""

        self.statusBar.showMessage(f"Line: {self.line} | Column: {self.column} | Characters: {self.char_count} | Encoding: {self.encoding} {asterisk}")


if __name__ == '__main__':
    app = QApplication(sys.argv)

    loadStyle()
    
    file_to_open = None
    if len(sys.argv) > 1:
        file_to_open = sys.argv[1]

    scratchpad = Scratchpad(file_to_open)
    scratchpad.show()
    sys.exit(app.exec_())
