
"""python plugin for substance painter 2020+.
Export substance painter maps to a RenderMan Asset package.
"""
# -----------------------------------------------------------------------------
#  MIT License
#
#  Copyright (c) 2016 Philippe Leprince
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
# -----------------------------------------------------------------------------

import os
import inspect
import json
from functools import partial
# from PySide2 import (QtWidgets, QtGui, QtCore)   # pylint: disable=import-error
from PySide2.QtCore import (QResource, Qt)   # pylint: disable=import-error
from PySide2.QtGui import (QIcon)   # pylint: disable=import-error
from PySide2.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QToolButton,
    QPushButton, QFrame, QSizePolicy, QFileDialog)   # pylint: disable=import-error
import substance_painter.ui as spui         # pylint: disable=import-error
import substance_painter.logging as spl     # pylint: disable=import-error

__version__ = '2.0.0a1'


def root_dir():
    """Returns the path the dir from which this plugin is executed."""
    try:
        this_file_path = __file__
    except NameError:
        this_file_path = os.path.abspath(inspect.stack()[0][1])
    root = os.path.dirname(this_file_path)
    return root


def pick_directory(*args):
    libpath = QFileDialog.getExistingDirectory(
        None, 'Select a directory...')
    args[0].setText(libpath)
    spl.info(str(args))


class Prefs(object):

    def __init__(self):
        self.prefs = {}
        self.root = root_dir()
        self.file = os.path.join(self.root, 'renderman.prefs')
        self.load()

    def load(self):
        if os.path.exists(self.file):
            with open(self.file, 'r') as fhdl:
                self.prefs = json.load(fhdl)

    def save(self):
        with open(self.file, mode='w') as fhdl:
            json.dump(self.prefs, fhdl)
        spl.info('PREFS SAVED')

    def set(self, key, val):
        self.prefs[key] = val

    def get(self, key, default):
        return self.prefs.get(key, default)

    def __del__(self):
        self.save()


class RenderManForSP(object):

    def __init__(self):
        self.root = root_dir()
        self.widgets = []
        spl.info('root = %s' % self.root)
        rpath = os.path.join(self.root, 'renderman.rcc')
        rloaded = QResource.registerResource(rpath)
        if not rloaded:
            spl.error('Invalid Resource: %s', rpath)
        self.prefs = Prefs()
        self.build_panel()

    def __del__(self):
        spl.info('DELETE !!')
        for widget in self.widgets:
            spui.delete_ui_element(widget)

    def filepath_field(self, label, text, changed=None, icon=None, placeholder=None):
        lyt = QHBoxLayout()
        lbl = QLabel(label)
        lyt.addWidget(lbl)
        fld = QLineEdit()
        fld.setStyleSheet('color: #7795DF;')
        fld.setText(text)
        if placeholder is not None:
            fld.setPlaceholderText(placeholder)
        if changed is not None:
            fld.textChanged.connect(changed)
        lyt.addWidget(fld)
        but = QToolButton()
        if icon is not None:
            spl.info(' + icon = %s' % icon)
            icon = QIcon(icon)
            but.setIcon(icon)
        but.clicked.connect(partial(pick_directory, fld))
        lyt.addWidget(but)
        for i, s in [(0, 0), (1, 1), (2, 0)]:
            lyt.setStretch(i, s)
        return lyt

    def build_panel(self):
        """Build the UI"""
        spl.info('build_panel')
        # Create a simple text widget
        root = QWidget()
        root.setWindowTitle("RenderMan")
        # Add this widget as a dock to the interface
        spui.add_dock_widget(root)

        vlyt = QVBoxLayout()
        # vlyt.setContentsMargins(5, 10, 5, 10)
        vlyt.setSpacing(10)
        root.setLayout(vlyt)
        # top buttons
        hlyt1 = QHBoxLayout()
        vlyt.addLayout(hlyt1)
        but1 = QPushButton(QIcon(':PxrSurface_hover.svg'), 'PxrSurface')
        but2 = QPushButton(QIcon(':PxrDisney_hover.svg'), 'PxrDisney')
        hlyt1.addWidget(but1)
        hlyt1.addWidget(but2)
        hlyt1.addStretch(1)
        vers = QLabel('<p style="color: #666;">%s</p>' % __version__)
        vers.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        hlyt1.addWidget(vers)
        # hline
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(1)
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line.setStyleSheet('background-color: #262626;')
        vlyt.addWidget(line)
        # prefs
        vlyt2 = QVBoxLayout()
        vlyt2.setSpacing(5)
        vlyt.addLayout(vlyt2)
        vlyt2.addLayout(
            self.filepath_field('RenderMan Pro Server:', self.prefs.get('RMANTREE', ''),
                                partial(self.prefs.set, 'RMANTREE'),
                                icon=':folder.svg', placeholder='$RMANTREE'))
        vlyt2.addLayout(
            self.filepath_field('Export to:', self.prefs.get('saveTo', ''),
                                partial(self.prefs.set, 'saveTo'),
                                icon=':folder.svg'))
        # keep ui at top of layout
        vlyt.addStretch(1)
        # Store added widget for proper cleanup when stopping the plugin
        self.widgets.append(root)
        spl.info('  |_ done')


def start_plugin():
    """This method is called when the plugin is started."""
    setattr(start_plugin, 'obj', RenderManForSP())
    spl.info('RenderMan started')


def close_plugin():
    """This method is called when the plugin is stopped."""
    # We need to remove all added widgets from the UI.
    setattr(start_plugin, 'obj', None)
    spl.info('RenderMan stopped')


if __name__ == "__main__":
    start_plugin()
