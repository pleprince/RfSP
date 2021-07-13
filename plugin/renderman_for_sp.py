
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

# TODO: make sure the normals are in directX format
# TODO: remove non-exportable channels for def.
# TODO: add anisotropy
# TODO: name textures with color spaces
# pylint: disable=missing-docstring,invalid-name,import-error

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
from PySide2.QtCore import (QResource, Qt)
from PySide2.QtGui import (QIcon)
from PySide2.QtWidgets import (
    QWidget,
    QMessageBox,
    QFileDialog,
    QFormLayout,
    QComboBox,
    QProgressDialog,
    QApplication
    )
import substance_painter as sp
import substance_painter.ui as spui
import substance_painter.logging as spl
import substance_painter.project as spp
import substance_painter.textureset as spts
import substance_painter.export as spex


__version__ = '24.1.0'
MIN_RPS = '24.1'
MIN_SP_API = '0.1.0'


class Log(object):
    def __init__(self, loglevel=spl.ERROR):
        self.channel = 'RenderMan %s' % __version__
        self.loglevel = int(loglevel)
        self.info('Log Level: %s (%s)', loglevel, self.loglevel)
        pyv = sys.version_info
        self.info('SP python: %d.%d.%d', *tuple(pyv[0:3]))

    def debug_error(self, msg, *args):
        if self.loglevel >= int(spl.DBG_ERROR):     # 5
            spl.log(spl.ERROR, self.channel, msg % args)

    def debug_warning(self, msg, *args):
        if self.loglevel >= int(spl.DBG_WARNING):    # 4
            spl.log(spl.WARNING, self.channel, msg % args)

    def debug_info(self, msg, *args):
        if self.loglevel >= int(spl.DBG_INFO):       # 3
            spl.log(spl.INFO, self.channel, msg % args)

    def error(self, msg, *args):
        if self.loglevel >= int(spl.ERROR):          # 2
            spl.log(spl.ERROR, self.channel, msg % args)

    def warning(self, msg, *args):
        if self.loglevel >= int(spl.WARNING):        # 1
            spl.log(spl.WARNING, self.channel, msg % args)

    def info(self, msg, *args):
        if self.loglevel >= int(spl.INFO):           # 0
            spl.log(spl.INFO, self.channel, msg % args)


LOG = Log(loglevel=spl.ERROR)


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
        LOG.debug_info('Prefs created')

    def load(self):
        if os.path.exists(self.file):
            with open(self.file, 'r') as fhdl:
                self.prefs = json.load(fhdl)
            LOG.debug_info('Loaded: %s', self.file)
        else:
            LOG.debug_warning('NOT loaded: %s', self.file)

    def save(self):
        with open(self.file, mode='w') as fhdl:
            json.dump(self.prefs, fhdl, sort_keys=False, indent=4)
        LOG.debug_info('PREFS SAVED: %s', self.file)

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
        LOG.debug_info('root = %r', self.root)
        # load resource file
        rpath = os.path.join(self.root, 'renderman.rcc')
        rloaded = QResource.registerResource(rpath)
        if not rloaded:
            LOG.error('Invalid Resource: %s', rpath)
        # init UI
        self.prefs = Prefs()
        self.widget, self.dock = self.build_panel()

    def cleanup(self):
        LOG.debug_info('cleanup')
        self.prefs.save()
        spui.delete_ui_element(self.dock)

    def build_panel(self):
        """Build the UI"""
        LOG.debug_info('build_panel')
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
                    self.spx_num_textures = 0
                    self.spx_progress = None
                    self.opt_bxdf = None
                    self.opt_ocio = None
                    self._defaultLabel = 'UNTITLED'
                    self.ocio_config = {'config': None, 'path': None}
                    # render previews
                    self.hostTree = ''
                    self.rmanTree = self.prefsobj.get('RMANTREE', '')
                    LOG.debug_info('SPrefs object created')

                def getHostPref(self, pref_name, default_value):
                    return self.prefsobj.get(pref_name, default_value)

                def setHostPref(self, pref_name, value):
                    prefs = self.prefsobj.get('host_prefs', {})
                    prefs[pref_name] = value
                    self.prefsobj.set('host_prefs', prefs)
                    # self._print()

                def saveAllPrefs(self):
                    for k in self.saved:
                        self.setHostPref(k, getattr(self, k))
                    # self._print()

                def preExportCheck(self, mode, hdr=None):
                    LOG.debug_info('preExportCheck: %r, hdr=%r', mode, hdr)
                    if mode == 'material':
                        try:
                            self._defaultLabel = spp.name() or 'UNTITLED'
                        except BaseException as err:
                            LOG.error('%s', err)
                            msg_box(str(err), '', QMessageBox.Ok, QMessageBox.Ok)
                            return False
                        return True
                    LOG.warning('Not supported (%s)', mode)
                    msg_box('This is not supported !', 'Sorry...',
                            QMessageBox.Ok, QMessageBox.Ok)
                    return False

                def exportMaterial(self, categorypath, infodict, previewtype):
                    LOG.debug_info(
                        'exportMaterial: %r, %r, %r', categorypath, infodict,
                        previewtype)
                    #
                    _bxdf = self.opt_bxdf.currentText()
                    self.prefsobj.set('last bxdf', _bxdf)
                    LOG.debug_info('chosen bxdf: %s', _bxdf)
                    _ocio = self.opt_ocio.currentText()
                    self.ocio_config['config'] = _ocio
                    if _ocio == '$OCIO':
                        self.ocio_config['path'] = FilePath(os.environ['OCIO'])
                    elif _ocio != 'Off':
                        self.ocio_config['path'] = FilePath(self.rmanTree).join(
                            'lib', 'ocio', _ocio, 'config.ocio')
                    self.prefsobj.set('ocio config', _ocio)
                    LOG.debug_info('chosen ocio config: %s', _ocio)
                    # setup data
                    bxdf_rules = self.rules['models'][_bxdf]
                    mappings = bxdf_rules['mapping']
                    graph = bxdf_rules.get('graph', None)
                    settings = bxdf_rules.get('settings', None)
                    scene = infodict['label']

                    # we save the assets to SP's export directory, because we
                    # know it is writable. We will move them to the requested
                    # location later.
                    export_path = FilePath(tempfile.mkdtemp(prefix='rfsp_export_'))

                    # export project textures
                    self.sp_export(export_path)

                    # open progress dialog
                    self.spx_progress = QProgressDialog(
                        'Converting textures...', 'Cancel',
                        0, self.spx_num_textures - 1)
                    self.spx_progress.setMinimumDuration(1)
                    QApplication.processEvents()

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
                        LOG.debug_info('+ Exporting %s', label)

                        asset_path = export_path.join(label + '.rma')
                        LOG.debug_info('  + asset_path %s', asset_path)
                        asset_json_path = asset_path.join('asset.json')
                        LOG.debug_info('  + asset_json_path %s', asset_json_path)

                        # create asset directory
                        create_directory(asset_path)

                        # create asset
                        try:
                            asset = rac.RmanAsset(assetType='nodeGraph', label=label)
                        except Exception:
                            LOG.error('Asset creation failed')
                            raise

                        asset.ocio = self.ocio_config

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
                        LOG.debug_info('  + Root node: %s', root_node)

                        # add a disney, pixar or lama bxdf
                        #
                        bxdf_node = label + "_Srf"
                        asset.addNode(bxdf_node, _bxdf, 'bxdf', _bxdf)
                        LOG.debug_info('  + BxDF node: %s  (%s)', root_node, _bxdf)

                        # The bxdf may need specific settings to match Substance Painter
                        set_params(settings, 'bxdf', bxdf_node, asset)

                        # connect surf to root node
                        #
                        asset.addConnection('%s.outColor' % bxdf_node,
                                            '%s.surfaceShader' % root_node)

                        # build additional nodes if need be.
                        #
                        if graph:
                            LOG.debug_info('  + Create graph nodes...')
                            for nname, ndict in graph['nodes'].items():
                                lname = label + nname
                                asset.addNode(lname, ndict['nodetype'],
                                              ndict.get('category', 'pattern'),
                                              ndict['nodetype'])
                                LOG.debug_info(
                                    '    |_ %s  (%s)', lname, ndict['nodetype'])
                                if 'params' in ndict:
                                    for pname, pdict in ndict['params'].items():
                                        asset.addParam(lname, pname, pdict)
                                        LOG.debug_info(
                                            '       |_ param: %s %s = %s',
                                            pdict['type'], pname, pdict['value'])

                        # create texture nodes
                        LOG.debug_info('  + Create texture nodes...')
                        chan_nodes = {}
                        for ch_type in chans:
                            fpath_list = self.spx_exported_files[mat.name()].get(ch_type, None)
                            if fpath_list is None:
                                LOG.debug_warning(
                                    '    |_ tex_dict[%r][%r] failed', mat.name(),
                                    ch_type)
                                continue
                            node_name = "%s_%s_tex" % (label, ch_type)
                            LOG.debug_info('    |_ %s', node_name)
                            chan_nodes[ch_type] = node_name
                            colorspace = mappings[ch_type]['ocio']
                            fpath = self.txmake(is_udim, asset_path, fpath_list,
                                                self.ocio_config, colorspace)
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
                        LOG.debug_info('  + Direct connections...')
                        for ch_type in chans:
                            if not ch_type in mappings:
                                LOG.debug_warning('    |_ skipped %r', ch_type)
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
                                    LOG.debug_warning('WARNING: Not connecting: %s', ch_type)
                                continue
                            if dst_param == 'graph':
                                continue
                            dst = '%s.%s' % (bxdf_node, dst_param)
                            asset.addConnection(src, dst)
                            LOG.debug_info('    |_ connect: %s -> %s' % (src, dst))
                            # also tag the bxdf param as connected
                            pdict = {'type': 'reference ' + dst_type, 'value': None}
                            asset.addParam(bxdf_node, dst_param, pdict)
                            LOG.debug_info(
                                '       |_ param: %s %s -> %s', pdict['type'],
                                dst_param, pdict['value'])

                        # make graph connections
                        #
                        if graph and 'connections' in graph:
                            LOG.debug_info('  + Connect graph nodes...')
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
                                LOG.debug_info('    |_ connect: %s -> %s', src, dst)
                                # mark param as a connected
                                dstType = con['dst']['type']
                                pdict = {'type': 'reference %s' % dstType, 'value': None}
                                asset.addParam(dst_node, con['dst']['param'], pdict)
                                LOG.debug_info(
                                    '       |_ param: %s %s = %s',
                                    pdict['type'], con['dst']['param'],
                                    pdict['value'])

                        # save asset
                        #
                        LOG.debug_info('  + ready to save: %s' % asset_json_path)
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
                        for _chan, fpath_list in chans.items():
                            for fpath in fpath_list:
                                if not os.path.exists(fpath):
                                    LOG.warning('cleanup: file not found: %s', fpath)
                                    continue
                                try:
                                    os.remove(fpath)
                                except (OSError, IOError):
                                    LOG.error('Cleanup failed: %s' % fpath)
                                else:
                                    LOG.debug_info('Cleanup: %s' % fpath)

                    # cleanup progress dialog
                    self.spx_progress.close()
                    del self.spx_progress
                    self.spx_progress = None
                    QApplication.processEvents()

                    LOG.debug_info('RenderMan : Done !')
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
                        self.opt_ocio.addItems(['Off', 'ACES-1.2',
                                                'filmic-blender', '$OCIO'])
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
                    LOG.debug_info(
                        '%r ------------------------\nLOADED:\n%s\nSTATE:\n%s', self,
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
                    meta['description'] = ('Created by RenderMan for Substance '
                                           'Painter %s' % __version__)
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
                    LOG.debug_info('  + compatibility set')

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
                    LOG.debug_info('+ Exported --------------------------------------------')
                    self.spx_exported_files = {}
                    self.spx_num_textures = 0
                    for stack, texs in result.textures.items():
                        LOG.debug_info('  |_ Stack %s: ', stack)
                        stck_name = stack[0]
                        self.spx_exported_files[stck_name] = {}
                        for t in texs:
                            LOG.debug_info('     |_ %s', t)
                            if t:
                                ch_type = re.search(r'_([A-Za-z]+)(\.\d{4})*\.\w{3}$', t).group(1)
                                if ch_type in self.spx_exported_files[stck_name]:
                                    self.spx_exported_files[stck_name][ch_type].append(t)
                                else:
                                    self.spx_exported_files[stck_name][ch_type] = [t]
                                self.spx_num_textures += 1

                def textureset_channels(self, spts_textureset):
                    result = {}
                    ts_name = spts_textureset.name()
                    chans = spts_textureset.get_stack().all_channels()
                    for chan_type in chans:
                        if ts_name in self.spx_exported_files:
                            ch = chan_type_str(chan_type)
                            result[chan_type_str(chan_type)] = \
                                self.spx_exported_files[ts_name].get(ch, [])
                    return result

                def txmake(self, is_udim, asset_path, fpath_list, ocio_config,
                           ocio_colorspace):

                    rmantree = FilePath(os.environ['RMANTREE'])
                    binary = rmantree.join('bin', app('txmake')).os_path()
                    cmd = [binary]
                    if is_udim:
                        cmd += ['-resize', 'round-',
                                '-mode', 'clamp',
                                '-format', 'openexr',
                                '-compression', 'pxr24',
                                '-newer']
                    else:
                        cmd += ['-resize', 'round-',
                                '-mode', 'periodic',
                                '-format', 'openexr',
                                '-compression', 'pxr24',
                                '-newer']
                    if ocio_config['path']:
                        cmd += ['-ocioconfig', ocio_config['path'],
                                '-ocioconvert', ocio_colorspace, 'rendering']
                    cmd += ['src', 'dst']
                    LOG.debug_info('       |_ cmd = %r', ' '.join(cmd))
                    for img in fpath_list:
                        img = FilePath(img)
                        self.spx_progress.setLabelText(
                            '  Converting %s...  ' % img.basename())
                        QApplication.processEvents()
                        cmd[-2] = img.os_path()
                        filename = img.basename()
                        texfile = os.path.splitext(filename)[0] + '.tex'
                        cmd[-1] = asset_path.join(texfile).os_path()
                        LOG.debug_info('       |_ txmake : %s -> %s',
                                       cmd[-2], cmd[-1])
                        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE,
                                             startupinfo=startup_info())
                        p.wait()
                        # update progress dialog
                        self.spx_progress.setValue(self.spx_progress.value() + 1)
                        QApplication.processEvents()
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

        LOG.debug_info('  |_ done')
        return root, dock


def pick_rmantree():
    rmantree = QFileDialog.getExistingDirectory(
        None,
        caption='Select your RenderManProServer %s+ directory' % MIN_RPS)
    if not 'RenderManProServer-' in rmantree:
        ret = msg_box(
            'This is not a RenderManProServer directory !',
            'This software needs RendermanProServer-%s+ to run.' % MIN_RPS,
            QMessageBox.Abort | QMessageBox.Retry, QMessageBox.Retry)
        if ret == QMessageBox.Abort:
            raise RuntimeError('This is not a RenderMan Pro Server directory')
        else:
            return pick_rmantree()
    return rmantree


def env_check(prefs):
    rmantree = prefs.get('RMANTREE', None)
    if rmantree is None or not os.path.exists(rmantree):
        rmantree = pick_rmantree()
        prefs.set('RMANTREE', rmantree)
    # check the version
    rps_version = re.search(r'RenderManProServer-([\d]+)', rmantree).group(1)
    if rps_version < MIN_RPS:
        ret = msg_box(
            'RenderMan version too old !',
            'This software needs RendermanProServer-%s+ to run.' % MIN_RPS,
            QMessageBox.Abort | QMessageBox.Retry, QMessageBox.Retry)
        if ret == QMessageBox.Retry:
            return env_check(prefs)
        raise RuntimeError(
            'This software needs RendermanProServer-%s+ to run.' % MIN_RPS)

    LOG.info('RMANTREE = %r', rmantree)
    os.environ['RMANTREE'] = rmantree
    rmp_path = os.path.join(rmantree, 'lib', 'python3.7', 'site-packages')
    if rmp_path not in sys.path:
        sys.path.append(rmp_path)
    rmu_path = os.path.join(rmantree, 'bin')
    if rmu_path not in sys.path:
        sys.path.append(rmu_path)
    return rps_version


def create_directory(dir_path):
    if not dir_path.exists():
        try:
            os.mkdir(dir_path.os_path())
        except (OSError, IOError):
            LOG.error('Asset directory could not be created !')
            raise
        LOG.debug_info('  + Created dir: %s', dir_path)
    else:
        LOG.debug_info('  + dir exists: %s', dir_path)


def set_params(settings_dict, chan, node_name, asset):
    # The bxdf may need specific settings to match Substance Painter
    try:
        params = settings_dict[chan]
    except (KeyError, TypeError):
        pass
    else:
        for pname, pdict in params.items():
            asset.addParam(node_name, pname, pdict)
            LOG.debug_info('       |_ param: %s %s = %s', pdict['type'],
                           pname, pdict['value'])


def add_texture_node(asset, node_name, ntype, filepath):
    asset.addNode(node_name, ntype, 'pattern', ntype)
    pdict = {'type': 'string', 'value': filepath.basename()}
    asset.addParam(node_name, 'filename', pdict)
    asset.addDependency(pdict['value'])


def chan_type_str(channel_type):
    return str(channel_type).split('.')[-1]


def print_dict(some_dict, msg=''):
    LOG.debug_info(msg + json.dumps(some_dict, indent=4))


def app(name):
    if os.name is 'nt':
        return name + '.exe'
    return name


def startup_info():
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


def msg_box(msg, infos, buttons, default_button):
    wdgt = QMessageBox()
    wdgt.setText(msg)
    wdgt.setInformativeText(infos)
    wdgt.setStandardButtons(buttons)
    wdgt.setDefaultButton(default_button)
    return wdgt.exec_()


# -----------------------------------------------------------------------------

def start_plugin():
    """This method is called when the plugin is started."""
    if sp.__version__ < MIN_SP_API:
        raise RuntimeError(
            'RenderMan for Substance Painter requires python API %s+ !' % MIN_SP_API)
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
