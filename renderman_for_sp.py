
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

# TODO: dialogs for unsupported stuff
# TODO: Colorspace UI
# TODO: Colorspace txmake
# TODO: ERROR if RPS version < 24.1
# TODO: File picker to RMANTREE
# TODO: Complain if python API < 0.1.0


import os
import sys
import traceback
import inspect
import json
# import logging
import tempfile
import getpass
import re
import subprocess
import shutil
# from functools import partial
# from PySide2 import (QtWidgets, QtGui, QtCore)  # pylint: disable=import-error
from PySide2.QtCore import (QResource, Qt)   # pylint: disable=import-error
from PySide2.QtGui import (QIcon)   # pylint: disable=import-error
from PySide2.QtWidgets import (
    QWidget,
    # QHBoxLayout,
    # QVBoxLayout,
    # QLabel,
    # QLineEdit,
    # QToolButton,
    # QPushButton,
    # QFrame,
    # QSizePolicy,
    QFileDialog,
    QFormLayout,
    QComboBox
    )   # pylint: disable=import-error
import substance_painter as sp              # pylint: disable=import-error
import substance_painter.ui as spui         # pylint: disable=import-error
import substance_painter.logging as spl     # pylint: disable=import-error
import substance_painter.project as spp     # pylint: disable=import-error
import substance_painter.textureset as spts # pylint: disable=import-error
# import substance_painter.resource as spr    # pylint: disable=import-error
import substance_painter.export as spex     # pylint: disable=import-error


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
        self.prefs.save()
        spui.delete_ui_element(self.dock)

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
        rman_version_str = env_check(self.prefs)
        try:
            import rman_utils.rman_assets as ra
            import rman_utils.rman_assets.core as rac
            import rman_utils.rman_assets.ui as rui
            import rman_utils.rman_assets.lib as ral
            # from rman_utils.rman_assets.common.ui_utils import createHLayout
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
                    self.root_dir = root_dir()
                    self.prefsobj = pref_obj
                    self.rules = self._load_rules()
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
                    # export vars
                    self.spx_exported_files = {}
                    self.opt_bxdf = None
                    self.opt_ocio = None
                    # render previews
                    self.hostTree = ''
                    self.rmanTree = self.prefsobj.get('RMANTREE', '')
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
                    LOG.info('exportMaterial: %r, %r, %r', categorypath, infodict, previewtype)
                    #
                    _bxdf = self.opt_bxdf.currentText()
                    _ocio = self.opt_ocio.currentText()
                    self.prefsobj.set('last bxdf', _bxdf)
                    LOG.info('chosen bxdf: %s', _bxdf)
                    # setup data
                    bxdf_rules = self.rules['models'][_bxdf]
                    mappings = bxdf_rules['mapping']
                    graph = bxdf_rules.get('graph', None)
                    settings = bxdf_rules.get('settings', None)
                    scene = infodict['label']

                    # we save the assets to SP's export directory, because we know it is writable.
                    # We will move them to the requested location later.
                    export_path = FilePath(tempfile.mkdtemp(prefix='rfsp_export_'))

                    # export project textures
                    self.sp_export(export_path)

                    # list of spts.TextureSet objects
                    tset_list = spts.all_texture_sets()

                    # build assets
                    asset_list = []
                    for mat in tset_list:
                        label = scene
                        is_udim = mat.has_uv_tiles()
                        if not is_udim:
                            label = '%s_%s' % (scene, mat.name())

                        # chans = mat.get_stack().all_channels()
                        chans = self.textureset_channels(mat)
                        LOG.info('+ Exporting %s', label)

                        asset_path = export_path.join(label + '.rma')
                        LOG.info('  + asset_path %s', asset_path)
                        asset_json_path = asset_path.join('asset.json')
                        LOG.info('  + asset_json_path %s', asset_json_path)

                        # create asset directory
                        create_directory(asset_path)

                        # create asset
                        try:
                            asset = rac.RmanAsset(assetType='nodeGraph', label=label)
                        except Exception:
                            LOG.error('Asset creation failed')
                            raise

                        # create standard metadata
                        #
                        self.set_metadata(asset, mat)

                        # create nodes
                        # start by adding a root node
                        #
                        root_node = label + '_Material'
                        asset.addNode(root_node, 'shadingEngine', 'root', 'shadingEngine')
                        pdict = {'type': 'reference float[]', 'value': None}
                        asset.addParam(root_node, 'surfaceShader', pdict)
                        LOG.info('  + Root node: %s', root_node)

                        # add a disney, pixar or lama bxdf
                        #
                        bxdf_node = label + "_Srf"
                        asset.addNode(bxdf_node, _bxdf, 'bxdf', _bxdf)
                        LOG.info('  + BxDF node: %s  (%s)', root_node, _bxdf)

                        # The bxdf may need specific settings to match Substance Painter
                        set_params(settings, 'bxdf', bxdf_node, asset)

                        # connect surf to root node
                        #
                        asset.addConnection('%s.outColor' % bxdf_node,
                                            '%s.surfaceShader' % root_node)

                        # build additional nodes if need be.
                        #
                        if graph:
                            LOG.info('  + Create graph nodes...')
                            for nname, ndict in graph['nodes'].items():
                                lname = label + nname
                                asset.addNode(lname, ndict['nodetype'],
                                              ndict.get('category', 'pattern'),
                                              ndict['nodetype'])
                                LOG.info('    |_ %s  (%s)', lname, ndict['nodetype'])
                                if 'params' in ndict:
                                    for pname, pdict in ndict['params'].items():
                                        asset.addParam(lname, pname, pdict)
                                        LOG.info('       |_ param: %s %s = %s',
                                                 pdict['type'], pname, pdict['value'])

                        # create texture nodes
                        LOG.info('  + Create texture nodes...')
                        chan_nodes = {}
                        for ch_type in chans:
                            fpath_list = self.spx_exported_files[mat.name()].get(ch_type, None)
                            if fpath_list is None:
                                LOG.warning('    |_ tex_dict[%r][%r] failed', mat.name(), ch_type)
                                continue
                            node_name = "%s_%s_tex" % (label, ch_type)
                            LOG.info('    |_ %s', node_name)
                            chan_nodes[ch_type] = node_name
                            fpath = self.txmake(is_udim, asset_path, fpath_list)
                            if ch_type == 'Normal':
                                add_texture_node(asset, node_name, 'PxrNormalMap', fpath)
                            elif ch_type == 'Height':
                                add_texture_node(asset, node_name, 'PxrBump', fpath)
                            else:
                                add_texture_node(asset, node_name, 'PxrTexture', fpath)
                            set_params(settings, ch_type, node_name, asset)

                        # print_dict(chan_nodes, msg='chan_nodes:\n')

                        # make direct connections
                        #
                        LOG.info('  + Direct connections...')
                        for ch_type in chans:
                            if not ch_type in mappings:
                                LOG.warning('    |_ skipped %r', ch_type)
                                continue
                            src = None
                            dst_type = mappings[ch_type]['type']
                            dst_param = mappings[ch_type]['param']
                            if dst_type == 'normal':
                                src = '%s.resultN' % (chan_nodes[ch_type])
                            elif dst_type == 'color':
                                src = '%s.resultRGB' % (chan_nodes[ch_type])
                            elif dst_type == 'float':
                                src = '%s.resultR' % (chan_nodes[ch_type])
                            else:
                                # don't create a connection
                                if dst_param != 'graph':
                                    # connections with a graph type will be handled later, so
                                    # we don't warn in that case.
                                    LOG.warning('WARNING: Not connecting: %s', ch_type)
                                continue
                            if dst_param == 'graph':
                                continue
                            dst = '%s.%s' % (bxdf_node, dst_param)
                            asset.addConnection(src, dst)
                            LOG.info('    |_ connect: %s -> %s' % (src, dst))
                            # also tag the bxdf param as connected
                            pdict = {'type': 'reference ' + dst_type, 'value': None}
                            asset.addParam(bxdf_node, dst_param, pdict)
                            LOG.info('       |_ param: %s %s -> %s', pdict['type'],
                                     dst_param, pdict['value'])

                        # make graph connections
                        #
                        if graph and 'connections' in graph:
                            LOG.info('  + Connect graph nodes...')
                            for con in graph['connections']:

                                src_node = con['src']['node']
                                src_ch = None
                                if src_node == _bxdf:
                                    src_node = bxdf_node
                                elif src_node.startswith('ch:'):
                                    src_ch = src_node[3:]
                                    if src_ch in chan_nodes:
                                        src_node = chan_nodes[src_ch]
                                    else:
                                        continue
                                if not src_node.startswith(label):
                                    src_node = label + src_node
                                src = '%s.%s' % (src_node, con['src']['param'])

                                dst_node = con['dst']['node']
                                dst_ch = None
                                if dst_node == _bxdf:
                                    dst_node = bxdf_node
                                elif dst_node.startswith('ch:'):
                                    dst_ch = dst_node[3:]
                                    if dst_ch in chan_nodes:
                                        dst_node = chan_nodes[dst_ch]
                                    else:
                                        continue
                                if not dst_node.startswith(label):
                                    dst_node = label + dst_node
                                dst = '%s.%s' % (dst_node, con['dst']['param'])
                                asset.addConnection(src, dst)
                                LOG.info('    |_ connect: %s -> %s', src, dst)
                                # mark param as a connected
                                dstType = con['dst']['type']
                                pdict = {'type': 'reference %s' % dstType, 'value': None}
                                asset.addParam(dst_node, con['dst']['param'], pdict)
                                LOG.info('       |_ param: %s %s = %s',
                                         pdict['type'], con['dst']['param'],
                                         pdict['value'])

                        # save asset
                        #
                        LOG.info('  + ready to save: %s' % asset_json_path)
                        try:
                            asset.save(asset_json_path, False)
                        except:
                            LOG.error('Saving the asset failed !')
                            raise

                        # mark this asset as ready to be moved
                        #
                        asset_list.append(asset_path)

                    # move assets to the requested location
                    #
                    dst = ral.getAbsCategoryPath(self.cfg, categorypath)
                    for item in asset_list:
                        # if the asset already exists in the destination
                        # location, we need to move it first.
                        dst_asset = os.path.join(dst, os.path.basename(item))
                        if os.path.exists(dst_asset):
                            try:
                                os.rename(dst_asset, dst_asset + '_old')
                            except (OSError, IOError):
                                LOG.error('Could not rename asset to %s_old' % dst_asset)
                                continue
                            else:
                                shutil.rmtree(dst_asset + '_old', ignore_errors=False)
                        try:
                            shutil.move(item, dst)
                        except (OSError, IOError):
                            LOG.error('WARNING: Could not copy asset to %s' % dst)


                    # clean-up intermediate files
                    for mat in tset_list:
                        for chan, fpath_list in chans.items():
                            for fpath in fpath_list:
                                if not os.path.exists(fpath):
                                    LOG.warning('cleanup: file not found: %s', fpath)
                                    continue
                                try:
                                    os.remove(fpath)
                                except (OSError, IOError):
                                    LOG.error('Cleanup failed: %s' % fpath)
                                else:
                                    LOG.info('Cleanup: %s' % fpath)

                    LOG.info('RenderMan : Done !')
                    return True

                def addUiExportOptions(self, top_layout, mode):
                    if mode == 'material':
                        lyt = QFormLayout()
                        lyt.FieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
                        lyt.setContentsMargins(5, 5, 5, 5)
                        lyt.setSpacing(5)
                        lyt.setLabelAlignment(Qt.AlignRight)
                        # BXDF
                        self.opt_bxdf = QComboBox()
                        self.opt_bxdf.addItems(list(self.rules['models'].keys()))
                        lyt.addRow('BxDF :', self.opt_bxdf)
                        # color space
                        self.opt_ocio = QComboBox()
                        self.opt_ocio.addItems(['Off', 'ACES-1.2', 'Filmic-Blender'])
                        lyt.addRow('Color configuration :', self.opt_ocio)
                        # add to parent layout
                        top_layout.addLayout(lyt)
                        # set last used bxdf and ocio config
                        last_bxdf = self.prefsobj.get('last bxdf', None)
                        if last_bxdf:
                            self.opt_bxdf.setCurrentText(last_bxdf)
                        ocio_config = self.prefsobj.get('ocio config', None)
                        if ocio_config:
                            self.opt_ocio.setCurrentText(ocio_config)

                def _print(self):
                    prefs = self.prefsobj.get('host_prefs', {})
                    loaded = ['\t%s: %s\n' % (k, prefs[k]) for k in prefs]
                    state = ['\t%s: %s\n' % (k, getattr(self, k)) for k in self.saved]
                    LOG.info('%r ------------------------\nLOADED:\n%s\nSTATE:\n%s', self,
                             ''.join(loaded), ''.join(state))

                def _load_rules(self):
                    fpath = FilePath(root_dir()).join('renderman_rules.json')
                    if fpath.exists():
                        with open(fpath, 'r') as hdl:
                            data = json.load(hdl)
                        return data
                    else:
                        LOG.error('RULES ARE MISSING: can not open %r', fpath)
                        return {}

                def set_metadata(self, asset, sp_ts):
                    meta = asset.stdMetadata()
                    meta['author'] = getpass.getuser()
                    meta['description'] = 'Created by RenderMan for Substance Painter 0.3.0'
                    res = sp_ts.get_resolution()
                    meta['resolution'] = '%d x %d' %  (res.width, res.height)
                    for k, v in meta.items():
                        asset.addMetadata(k, v)
                    # Compatibility data
                    # This will help other application decide if they can use this asset.
                    #
                    asset.setCompatibility(
                        hostName='Substance Painter',
                        hostVersion=sp.__version__,
                        rendererVersion=str(self.rman_version))
                    LOG.info('  + compatibility set')

                def sp_export(self, export_path):
                    tset_names = [s.name() for s in spts.all_texture_sets()]
                    config = dict(self.rules['export_config'])
                    tex_path = export_path.join('exported')
                    create_directory(tex_path)
                    config['exportPath'] = tex_path.os_path()
                    # config['defaultExportPreset'] = spr.ResourceID(
                    #     context='allegorithmic', name='Renderman (pxrDisney)').url()
                    config['exportList'] = [{'rootPath': n} for n in tset_names]
                    # print_dict(config, msg='config:\n')
                    result = spex.export_project_textures(config)
                    if result.status != spex.ExportStatus.Success:
                        LOG.error(result.message)
                        raise RuntimeError(result.message)
                    LOG.info('+ Exported --------------------------------------------')
                    self.spx_exported_files = {}
                    for stack, texs in result.textures.items():
                        LOG.info('  |_ Stack %s: ', stack)
                        stck_name = stack[0]
                        self.spx_exported_files[stck_name] = {}
                        for t in texs:
                            LOG.info('     |_ %s', t)
                            if t:
                                ch_type = re.search(r'_([A-Za-z]+)(\.\d{4})*\.\w{3}$', t).group(1)
                                if ch_type in self.spx_exported_files[stck_name]:
                                    self.spx_exported_files[stck_name][ch_type].append(t)
                                else:
                                    self.spx_exported_files[stck_name][ch_type] = [t]
                    # print_dict(self.spx_exported_files, msg='spx_exported_files:\n')

                def textureset_channels(self, spts_textureset):
                    result = {}
                    ts_name = spts_textureset.name()
                    chans = spts_textureset.get_stack().all_channels()
                    for chan_type in chans:
                        if ts_name in self.spx_exported_files:
                            ch = chan_type_str(chan_type)
                            # ch_files = [f for f in self.spx_exported_files[ts_name] if ch in f]
                            result[chan_type_str(chan_type)] = self.spx_exported_files[ts_name].get(ch, [])
                    # print_dict(result, msg='[textureset_channels]  %s:\n' % ts_name)
                    return result

                def txmake(self, is_udim, asset_path, fpath_list):

                    rmantree = FilePath(os.environ['RMANTREE'])
                    binary = rmantree.join('bin', app('txmake')).os_path()
                    cmd = [binary]
                    if is_udim:
                        cmd += ['-resize', 'round-',
                                '-mode', 'clamp',
                                '-format', 'pixar',
                                '-compression', 'lossless',
                                '-newer',
                                'src', 'dst']
                    else:
                        cmd += ['-resize', 'round-',
                                '-mode', 'periodic',
                                '-format', 'pixar',
                                '-compression', 'lossless',
                                '-newer',
                                'src', 'dst']
                    for img in fpath_list:
                        img = FilePath(img)
                        cmd[-2] = img.os_path()
                        filename = img.basename()
                        texfile = os.path.splitext(filename)[0] + '.tex'
                        cmd[-1] = asset_path.join(texfile).os_path()
                        LOG.info('       |_ txmake : %s -> %s', cmd[-2], cmd[-1])
                        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE,
                                             startupinfo=startupInfo())
                        p.wait()

                    # return a local path to the tex file.
                    filename = FilePath(fpath_list[0]).basename()
                    fname, _ = os.path.splitext(filename)
                    asset_file_ref = FilePath(asset_path).join(fname + '.tex')
                    if is_udim:
                        asset_file_ref = re.sub(r'1\d{3}', '<UDIM>', asset_file_ref)
                    return FilePath(asset_file_ref)


            root.setWindowFlag(Qt.SubWindow, True)
            try:
                self.aui = rui.Ui(SPrefs(rman_version_str, self.prefs), parent=root)
            except BaseException:
                traceback.print_exc(file=sys.stdout)
            else:
                root.setLayout(self.aui.topLayout)

        LOG.info('  |_ done')
        return root, dock


def env_check(prefs):
    rmantree = prefs.get('RMANTREE', '')
    LOG.info('RMANTREE = %r', rmantree)
    # TODO: open file chooser
    os.environ['RMANTREE'] = rmantree
    rmp_path = os.path.join(rmantree, 'lib', 'python3.7', 'site-packages')
    if rmp_path not in sys.path:
        sys.path.append(rmp_path)
    rmu_path = os.path.join(rmantree, 'bin')
    if rmu_path not in sys.path:
        sys.path.append(rmu_path)
    return re.search(r'RenderManProServer-([\d]+)', rmantree).group(1)


def create_directory(dir_path):
    if not dir_path.exists():
        try:
            os.mkdir(dir_path.os_path())
        except (OSError, IOError):
            LOG.error('Asset directory could not be created !')
            raise
        LOG.info('  + Created dir: %s', dir_path)
    else:
        LOG.info('  + dir exists: %s', dir_path)


def set_params(settings_dict, chan, node_name, asset):
    # The bxdf may need specific settings to match Substance Painter
    try:
        params = settings_dict[chan]
    except (KeyError, TypeError):
        pass
    else:
        for pname, pdict in params.items():
            asset.addParam(node_name, pname, pdict)
            LOG.info('       |_ param: %s %s = %s', pdict['type'], pname, pdict['value'])


def add_texture_node(asset, node_name, ntype, filepath):
    asset.addNode(node_name, ntype, 'pattern', ntype)
    pdict = {'type': 'string', 'value': filepath.basename()}
    asset.addParam(node_name, 'filename', pdict)
    # if '_MAPID_' in filepath:
    #     asset.addParam(node_name, 'atlasStyle', {'type': 'int', 'value': 1})


def chan_type_str(channel_type):
    return str(channel_type).split('.')[-1]
    # return str(channel_type).split('.')[-1].lower()


def print_dict(some_dict, msg=''):
    LOG.info(msg + json.dumps(some_dict, indent=4))


def app(name):
    if os.name is 'nt':
        return (name + '.exe')
    return name


def startupInfo():
    """Returns a Windows-only object to make sure tasks launched through
    subprocess don't open a cmd window.

    Returns:
        subprocess.STARTUPINFO -- the properly configured object if we are on
                                  Windows, otherwise None
    """
    startupinfo = None
    if os.name is 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startupinfo


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
