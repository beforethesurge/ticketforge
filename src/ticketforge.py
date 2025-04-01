"""Template editor application for managing and using text templates.

This application provides a GUI interface for creating, editing, and managing
text templates. It supports template categories, variable input fields, and 
automatic updates. Templates can be organized into categories and contain 
dynamic input fields marked with [field_name].
"""

import ctypes
import json
import os
import sys
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Local imports
from updater import Updater


class InputDialog(QDialog):
    """Dialog for collecting user input for template fields.
    
    Displays a form with text input fields for each template variable.
    Creates a dynamic form based on fields found in template text.
    """

    def __init__(self, fields, parent=None):
        """Initialize the input dialog with given fields."""
        super().__init__(parent)
        self.fields = fields
        self.inputs = {}
        self.init_ui()

    def init_ui(self):
        """Set up the user interface for the input dialog."""
        self.setWindowTitle("Fill Template")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        layout = QFormLayout()

        for field in self.fields:
            self.inputs[field] = QLineEdit()
            layout.addRow(f"{field}:", self.inputs[field])

        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        layout.addRow(btn_ok)

        self.setLayout(layout)


class TemplateEditWindow(QMainWindow):
    """Window for editing and previewing a single template.
    
    Provides a split view with an editor pane and preview pane.
    Allows real-time preview of template with placeholder values.
    Supports saving changes and copying filled templates to clipboard."""
    
    def __init__(self, category, template_name, template_text, parent=None):
        """Initialize template editor window.
        
        Args:
            category (str): Category the template belongs to
            template_name (str): Name of the template being edited
            template_text (str): Initial template content
            parent (QWidget, optional): Parent widget for this window"""
        
        super().__init__(parent)
        self.category = category
        self.template_name = template_name
        self.template_text = template_text
        self.init_ui()

    def init_ui(self):
        """Set up the editor window UI."""
        self.setWindowTitle(f"Edit Template - {self.template_name}")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        #self.setGeometry(150, 150, 800, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Editor section
        editor_label = QLabel("Template Editor:")
        editor_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.editor = QTextEdit()
        self.editor.setText(self.template_text)
        
        # Preview section
        preview_label = QLabel("Template Preview:")
        preview_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        
        # Action buttons
        action_buttons = QHBoxLayout()
        btn_save = QPushButton("Save Template Changes")
        btn_copy = QPushButton("Fill Out and Copy")
        btn_save.clicked.connect(self.save_changes)
        btn_copy.clicked.connect(self.copy_to_clipboard)
        action_buttons.addWidget(btn_save)
        action_buttons.addWidget(btn_copy)
        
        # Help section
        help_text = (
            "Template Input Field Help:\n"
            "To create an input field, use square brackets with a field name:\n"
            "Example: [field_name]"
        )
        help_label = QLabel(help_text)
        
        # Add all elements to layout
        layout.addWidget(editor_label)
        layout.addWidget(self.editor)
        layout.addWidget(preview_label)
        layout.addWidget(self.preview)
        layout.addLayout(action_buttons)
        layout.addWidget(help_label)

        # Update preview
        self.update_preview()
        self.editor.textChanged.connect(self.update_preview)

    def update_preview(self):
        """Update the preview pane with current template content.
        
        Replaces template variables [field_name] with <field_name> 
        to show where variables will be inserted.
        """
        template_text = self.editor.toPlainText()
        preview_text = template_text
        fields = self.get_template_fields(template_text)
        for field in fields:
            preview_text = preview_text.replace(f'[{field}]', f'<{field}>')
        self.preview.setText(preview_text)

    def save_changes(self):
        """Save template changes back to parent TemplateEditor.
        
        Updates the template content in the main data dictionary
        and saves changes to disk.
        """
        if isinstance(self.parent(), TemplateEditor):
            self.parent().update_template(
                self.category,
                self.template_name,
                self.editor.toPlainText()
            )

    def copy_to_clipboard(self):
        """Fill out template and copy to clipboard."""
        template_text = self.editor.toPlainText()
        fields = self.get_template_fields(template_text)
        
        if fields:
            dialog = InputDialog(fields, self)
            if dialog.exec():
                filled_text = template_text
                for field in fields:
                    filled_text = filled_text.replace(
                        f'[{field}]', 
                        dialog.inputs[field].text()
                    )
                QApplication.clipboard().setText(filled_text)
                QMessageBox.information(
                    self, 
                    "Success", 
                    "Filled template copied to clipboard!"
                )
        else:
            QApplication.clipboard().setText(template_text)
            QMessageBox.information(
                self, 
                "Success", 
                "Template copied to clipboard!"
            )

    def get_template_fields(self, template_text):
        """Extract input fields from template text"""
        fields = []
        start = 0

        while True:
            start = template_text.find('[', start)
            if start == -1:
                break
            end = template_text.find(']', start)
            if end == -1:
                break
            fields.append(template_text[start + 1:end])
            start = end + 1

        return fields

class TemplateEditor(QMainWindow):
    """Main window for template editing and management.
    
    Provides interface for:
    - Managing template categories
    - Creating/editing/deleting templates
    - Filling out templates
    - Checking for application updates"""

    def __init__(self):
        """Initialize the template editor."""
        super().__init__()
        self.updater = Updater(self)
        local_version = self.updater.get_local_version()

        self.setWindowTitle(f"TicketForge v{local_version}")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon('img/icon.ico'))
        
        self.data = {}
        self.current_template = None
        self.current_category = None
            
        self.templates_file = 'data/templates.json'
        
        self.init_ui()
        self.load_templates()
        self.resize_and_center()

    def resize_and_center(self):
        """Resize window to content and center on screen."""
        self.adjustSize()
        
        # Get current screen
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        
        # Calculate center position
        center_point = screen_geometry.center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        
        # Move window
        self.move(frame_geometry.topLeft())

    def init_ui(self):
        """Set up the main user interface."""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Left panel setup
        left_panel = self._create_left_panel()
        
        # Right panel for updates
        right_panel = QVBoxLayout()
        update_button = QPushButton("Check for Updates")
        update_button.clicked.connect(self.updater.check_for_updates)
        
        right_panel.addWidget(update_button)
        right_panel.addStretch()
        
        # Add panels to layout
        layout.addWidget(left_panel)
        layout.addLayout(right_panel)

    def _create_left_panel(self):
        """Create and return the left panel with template management."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Tab widget for categories
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.category_changed)
        self.tab_widget.setMinimumWidth(350)
        
        # Template management buttons
        template_buttons = QHBoxLayout()
        btn_new_template = QPushButton("New Template")
        btn_delete_template = QPushButton("Delete Template")
        btn_new_template.clicked.connect(self.new_template)
        btn_delete_template.clicked.connect(self.delete_template)
        template_buttons.addWidget(btn_new_template)
        template_buttons.addWidget(btn_delete_template)
        
        # Category management buttons
        category_buttons = QHBoxLayout()
        btn_new_category = QPushButton("New Category")
        btn_delete_category = QPushButton("Delete Category")
        btn_new_category.clicked.connect(self.new_category)
        btn_delete_category.clicked.connect(self.delete_category)
        category_buttons.addWidget(btn_new_category)
        category_buttons.addWidget(btn_delete_category)
        
        layout.addWidget(self.tab_widget)
        layout.addLayout(template_buttons)
        layout.addLayout(category_buttons)
        
        return panel

    def load_templates(self):
        """Load templates from JSON file.
        
        Initializes with default "General" category if no templates exist."""

        if os.path.exists(self.templates_file):
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {"General": {}}  # Default category
            
        self.update_template_list()

    def save_templates(self):
        """Save templates to JSON file.
        
        Writes entire data dictionary to disk in pretty-printed JSON format."""
        with open(self.templates_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def update_template_list(self):
        """Refresh the template list UI.
        
        Creates tabs for each category.
        Populates lists with templates.
        Sets up context menus and event handlers."""
        self.tab_widget.clear()
        for category in self.data:
            list_widget = QListWidget()
            list_widget.addItems(self.data[category].keys())
            list_widget.itemClicked.connect(self.template_selected)
            list_widget.itemDoubleClicked.connect(self.edit_template)
            list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            list_widget.customContextMenuRequested.connect(
                self.show_template_context_menu
            )
            list_widget.setFixedWidth(330)
            self.tab_widget.addTab(list_widget, category)

    def show_template_context_menu(self, pos):
        """Show context menu for template actions."""
        list_widget = self.tab_widget.currentWidget()
        if not list_widget:
            return

        item = list_widget.itemAt(pos)
        if item:
            menu = QMenu()
            rename_action = menu.addAction("Rename Template")
            delete_action = menu.addAction("Delete Template")
            
            action = menu.exec(list_widget.mapToGlobal(pos))
            if action == rename_action:
                self.rename_template(item)
            elif action == delete_action:
                self.delete_template()

    def rename_template(self, item):
        """Rename the selected template."""
        if not self.current_category:
            return
            
        old_name = item.text()
        new_name, ok = QInputDialog.getText(
            self, "Rename Template", "Enter new template name:", text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            template_content = self.data[self.current_category][old_name]
            del self.data[self.current_category][old_name]
            self.data[self.current_category][new_name] = template_content
            self.save_templates()
            self.update_template_list()

    def category_changed(self, index):
        """Handle category change event."""
        if index >= 0:
            self.current_category = self.tab_widget.tabText(index)
            self.current_template = None

    def template_selected(self, item):
        """Handle template selection event."""
        self.current_template = item.text()
        self.current_category = self.tab_widget.tabText(
            self.tab_widget.currentIndex()
        )

    def edit_template(self, item):
        """Open template editor window for the selected template."""
        template_name = item.text()
        category = self.tab_widget.tabText(self.tab_widget.currentIndex())
        template_text = self.data[category][template_name]
        
        editor_window = TemplateEditWindow(
            category, template_name, template_text, self
        )
        editor_window.show()

    def update_template(self, category, template_name, new_text):
        """Update template content from editor window."""
        self.data[category][template_name] = new_text
        self.save_templates()

    def new_category(self):
        """Create a new template category."""
        name, ok = QInputDialog.getText(self, "New Category", "Enter category name:")
        if ok and name:
            if name in self.data:
                QMessageBox.warning(self, "Warning", "Category name already exists!")
                return
            self.data[name] = {}
            self.save_templates()
            self.update_template_list()

    def delete_category(self):
        """Delete the current category."""
        if self.current_category:
            reply = QMessageBox.question(
                self, 'Delete Category',
                f'Are you sure you want to delete "{self.current_category}"?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                del self.data[self.current_category]
                self.save_templates()
                self.update_template_list()
                self.current_category = None
                self.current_template = None

    def new_template(self):
        """Create new template in current category.
        
        Shows input dialog for template name.
        Validates name is unique within category.
        Initializes with default template text.
        """
        if not self.current_category:
            QMessageBox.warning(self, "Warning", "Please select a category first!")
            return
            
        name, ok = QInputDialog.getText(self, "New Template", "Enter template name:")
        if ok and name:
            if name in self.data[self.current_category]:
                QMessageBox.warning(self, "Warning", "Template name already exists!")
                return
                
            self.data[self.current_category][name] = (
                "Enter your template here.\nUse [field_name] for input fields."
            )
            self.save_templates()
            self.update_template_list()
            
            # Select the new template
            list_widget = self.tab_widget.currentWidget()
            items = list_widget.findItems(name, Qt.MatchFlag.MatchExactly)
            if items:
                list_widget.setCurrentItem(items[0])
                self.template_selected(items[0])

    def delete_template(self):
        """Delete currently selected template.
        
        Shows confirmation dialog.
        Removes template from dictionary and updates UI.
        """
        if self.current_template and self.current_category:
            reply = QMessageBox.question(
                self, 'Delete Template',
                f'Are you sure you want to delete "{self.current_template}"?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                del self.data[self.current_category][self.current_template]
                self.save_templates()
                self.update_template_list()
                self.current_template = None

    def get_template_fields(self, template_text):
        """Extract input fields from template text without using regex."""
        fields = []
        start = 0

        while True:
            start = template_text.find('[', start)
            if start == -1:
                break
            end = template_text.find(']', start)
            if end == -1:
                break
            fields.append(template_text[start + 1:end])
            start = end + 1

        return fields


def main():
    """Application entry point.
    
    Creates main application instance.
    Launches template editor window.
    Handles application lifecycle."""
    app = QApplication(sys.argv)
    
    # Set application ID for Windows taskbar icon
    if os.name == 'nt':  # Windows only
        myappid = 'ticketforge.template.editor'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
    icon_path = 'img/icon.ico'
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    editor = TemplateEditor()
    editor.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
