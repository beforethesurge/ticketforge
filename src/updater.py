'''Checks for updates via version file and downloads new version to ~\Downloads'
'''


import json
from os import path
from requests import get
from requests.exceptions import HTTPError
from PyQt6.QtWidgets import (QMessageBox, QWidget)


class Updater(QWidget):
    def __init__(self, root, local_file='data/version.json'):
        super().__init__()
        self.root = root
        self.local_file = local_file

    def check_for_updates(self):
        version_current = self.get_local_version()
        version_latest = self.get_remote_version()

        if version_latest is None:
            return

        if version_current != version_latest:
            self.prompt_update()
        else:
            QMessageBox.information(self, "Update", "No updates available")

    def get_local_version(self):
        with open(self.local_file, 'r') as file:
            version_local = json.load(file)
        return version_local["version"]

    def get_remote_version(self):
        with open(self.local_file, 'r') as file:
            version_remote_data = json.load(file)
            version_remote_url = version_remote_data["remote-version"]
        try:
            response = get(version_remote_url)
            response.raise_for_status()
            return response.json().get("version")
        except HTTPError as e:
            QMessageBox.warning(self, f"Warning", "Unable to check for updates: " + str(e))
            return None
        except Exception as e:
            QMessageBox.warning(self, f"Warning", "An error occurred: " + str(e))
            return None

    def prompt_update(self):
        response = QMessageBox.question(self, "Update", "New version available! Would you like to update?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if response == QMessageBox.StandardButton.Yes:
            self.download_update()

    def download_update(self):
        with open(self.local_file, 'r') as file:
            version_remote_installer = json.load(file)
            version_remote_installer = version_remote_installer["remote-installer"]
        install_file = get(version_remote_installer)
        install_file.raise_for_status()
        download_file = path.expanduser('~/Downloads/ticketforge-setup.exe')
        with open(download_file, 'wb') as file:
            file.write(install_file.content)
        QMessageBox.information(self, "Update", "Latest Installer is in your Downloads folder. Please overwrite your current installation")
        self.root.close()
