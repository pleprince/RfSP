
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
import sys
import traceback
import inspect
import json
import logging
from functools import partial
# from PySide2 import (QtWidgets, QtGui, QtCore)  # pylint: disable=import-error
from PySide2.QtCore import (QResource, Qt)   # pylint: disable=import-error
from PySide2.QtGui import (QIcon)   # pylint: disable=import-error
from PySide2.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QToolButton,
    QPushButton, QFrame, QSizePolicy, QFileDialog,
    QMenuBar)   # pylint: disable=import-error
import substance_painter.ui as spui         # pylint: disable=import-error
import substance_painter.logging as spl     # pylint: disable=import-error
import substance_painter.project as spp     # pylint: disable=import-error

__version__ = '2.0.0a1'


class Log():
    def __init__(self):
        self.channel = 'RenderMan %s' % __version__
        pyv = sys.version_info
        self.info('SP python: %d.%d.%d', *tuple(pyv[0:3]))

    def info(self, msg, *args):
        spl.log(spl.INFO, self.channel, msg % args)

    def warning(self, msg, *args):
        spl.log(spl.WARNING, self.channel, msg % args)

    def error(self, msg, *args):
        spl.log(spl.ERROR, self.channel, msg % args)


LOG = Log()


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
    LOG.info('pick_directory%s', str(args))


class Prefs(object):

    def __init__(self):
        self.prefs = {}
        self.root = root_dir()
        self.file = os.path.join(self.root, 'renderman.prefs')
        self.load()
        # LOG.info('Prefs created')

    def load(self):
        if os.path.exists(self.file):
            with open(self.file, 'r') as fhdl:
                self.prefs = json.load(fhdl)
            # LOG.info('Loaded: %s', self.file)
        # else:
        #     LOG.info('NOT loaded: %s', self.file)

    def save(self):
        with open(self.file, mode='w') as fhdl:
            json.dump(self.prefs, fhdl, sort_keys=False, indent=4)
        LOG.info('PREFS SAVED: %s', self.file)

    def set(self, key, val):
        self.prefs[key] = val

    def get(self, key, default):
        return self.prefs.get(key, default)

    def __del__(self):
        self.save()


class RenderManForSP(object):

    def __init__(self):
        # find root dir
        self.root = root_dir()
        LOG.info('root = %r', self.root)
        # load resource file
        rpath = os.path.join(self.root, 'renderman.rcc')
        rloaded = QResource.registerResource(rpath)
        if not rloaded:
            LOG.error('Invalid Resource: %s', rpath)
        # init UI
        self.prefs = Prefs()
        self.widget, self.dock = self.build_panel()

    def cleanup(self):
        LOG.info('cleanup')
        spui.delete_ui_element(self.dock)

    def filepath_field(self, label, text, changed=None, icon=None,
                       placeholder=None):
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
            LOG.info(' + icon = %s', icon)
            icon = QIcon(icon)
            but.setIcon(icon)
        but.clicked.connect(partial(pick_directory, fld))
        lyt.addWidget(but)
        for i, s in [(0, 0), (1, 1), (2, 0)]:
            lyt.setStretch(i, s)
        return lyt

    def build_panel(self):
        """Build the UI"""
        LOG.info('build_panel')
        # Create a simple text widget
        root = QWidget(None, Qt.Window)
        root.setWindowTitle("RenderMan")
        logo = QIcon(':R_logo.svg')
        logo.addFile(':R_logo_white.svg', mode=QIcon.Normal, state=QIcon.On)
        root.setWindowIcon(logo)
        # Add this widget as a dock to the interface
        dock = spui.add_dock_widget(root)

        # preset browser
        rmantree = self.prefs.get('RMANTREE', '')
        os.environ['RMANTREE'] = rmantree
        rmp_path = os.path.join(rmantree, 'lib', 'python3.7', 'site-packages')
        if rmp_path not in sys.path:
            sys.path.append(rmp_path)
        rmu_path = os.path.join(rmantree, 'bin')
        if rmu_path not in sys.path:
            sys.path.append(rmu_path)
        try:
            import rman_utils.rman_assets as ra
            import rman_utils.rman_assets.core as rac
            import rman_utils.rman_assets.ui as rui
            import rman_utils.rman_assets.lib as ral
            from rman_utils.filepath import FilePath
        except BaseException as err:
            LOG.error('Failed to import: %s', err)
            traceback.print_exc(file=sys.stdout)
        else:
            # ra.setLogLevel(logging.DEBUG)

            class SPrefs(ral.HostPrefs):
                saved = {
                    'rpbConfigFile': FilePath(''), 'rpbUserLibraries': [],
                    'rpbSwatchSize': 64, 'rpbSelectedPreviewEnv': 0,
                    'rpbSelectedCategory': 'Materials',
                    'rpbSelectedLibrary': FilePath(''),
                    'rpbRenderAllHDRs': False,
                    'rpbHideFactoryLib': False
                }

                def __init__(self, rman_version, pref_obj):
                    super(SPrefs, self).__init__(rman_version)
                    self.prefsobj = pref_obj
                    if 'host_prefs' in self.prefsobj.prefs:
                        hprefs = self.prefsobj.prefs['host_prefs']
                        for k in self.saved:
                            setattr(self, k, hprefs.get(k, self.saved[k]))
                            if k == 'rpbConfigFile':
                                self.rpbConfigFile = FilePath(
                                    self.rpbConfigFile)
                            elif k == 'rpbSelectedLibrary':
                                self.rpbSelectedLibrary = FilePath(
                                    self.rpbSelectedLibrary)
                            elif k == 'rpbUserLibraries' and self.rpbUserLibraries:
                                self.rpbUserLibraries = [
                                    FilePath(f) for f in self.rpbUserLibraries]
                    #     LOG.info('prefs data loaded')
                    # self._print()
                    # LOG.info('SPrefs object created')

                def getHostPref(self, prefName, defaultValue):
                    return self.prefsobj.get(prefName, defaultValue)

                def setHostPref(self, prefName, value):
                    prefs = self.prefsobj.get('host_prefs', {})
                    prefs[prefName] = value
                    self.prefsobj.set('host_prefs', prefs)
                    # self._print()

                def saveAllPrefs(self):
                    for k in self.saved:
                        self.setHostPref(k, getattr(self, k))
                    # self._print()

                def preExportCheck(self, mode, hdr=None):
                    LOG.info('preExportCheck: %r, hdr=%r', mode, hdr)
                    if mode == 'material':
                        try:
                            self._defaultLabel = spp.name() or 'UNTITLED'
                        except BaseException as err:
                            LOG.error('%s', err)
                            return False
                        return True
                    LOG.warning('Not supported (%s)', mode)
                    return False

                def exportMaterial(self, categorypath, infodict, previewtype):
                    pass

                def _print(self):
                    prefs = self.prefsobj.get('host_prefs', {})
                    loaded = ['\t%s: %s\n' % (k, prefs[k]) for k in prefs]
                    state = ['\t%s: %s\n' % (k, getattr(self, k)) for k in self.saved]
                    LOG.info('%r ------------------------\nLOADED:\n%s\nSTATE:\n%s', self,
                             ''.join(loaded), ''.join(state))

            root.setWindowFlag(Qt.SubWindow, True)
            try:
                self.aui = ra.ui.Ui(SPrefs('25.0b1', self.prefs), parent=root)
            except BaseException:
                traceback.print_exc(file=sys.stdout)
            else:
                root.setLayout(self.aui.topLayout)

        LOG.info('  |_ done')
        return root, dock

    def export(self, bxdf):
        LOG.info('export %s', bxdf)

# -----------------------------------------------------------------------------

def start_plugin():
    """This method is called when the plugin is started."""
    setattr(start_plugin, 'obj', RenderManForSP())
    LOG.info('RenderMan started')


def close_plugin():
    """This method is called when the plugin is stopped."""
    # We need to remove all added widgets from the UI.
    rman_obj = getattr(start_plugin, 'obj')
    rman_obj.cleanup()
    del rman_obj
    setattr(start_plugin, 'obj', None)
    LOG.info('RenderMan stopped')


if __name__ == "__main__":
    start_plugin()
