#!/bin/bash

pyinstaller dist/ticketforge.spec

'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' installer/ticketforge-installer.iss

pip freeze > requirements.txt
