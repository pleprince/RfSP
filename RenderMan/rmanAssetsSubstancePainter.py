"""python 2.7 plugin for substance painter 2.3+
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


# standard imports first
import os
import os.path
import sys
import re
import json
import shutil
import logging
import getpass
import subprocess

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
LOGFILE = os.path.join(THIS_DIR, 'rfsp_log.txt')
logging.basicConfig(filename=LOGFILE,
                    filemode='w',
                    level=logging.DEBUG,
                    format='%(levelname)-10s %(message)s')
DBUG = logging.debug
INFO = logging.info
WARN = logging.warning
ERR = logging.error
XCPT = logging.exception
IMG_EXTS = ['.png', '.jpg', '.exr']
TEX_EXTS = ['.tex', '.tx', '.txr']


class FilePath(unicode):
    """A class based on unicode to handle filepaths on various OS platforms.

    Extends:
        unicode
    """

    def __new__(cls, path):
        """Create new unicode file path in POSIX format. Windows paths will be
        converted.

        Arguments:
            path {str} -- a file path, in any format.
        """
        fpath = path
        if os.sep is not '/':
            fpath = fpath.replace(os.sep, '/')
        return unicode.__new__(cls, fpath)

    def osPath(self):
        """return the platform-specif path, i.e. convert to windows format if
        need be.

        Returns:
            str -- a path formatted for the current OS.
        """
        return r'%s' % os.path.normpath(self)

    def exists(self):
        """Check is the path actually exists, using os.path.

        Returns:
            bool -- True if the path exists.
        """
        return os.path.exists(self)

    def join(self, *args):
        """Combine the arguments with the current path and return a new
        FilePath object.

        Arguments:
            *args {list} -- a list of path segments.

        Returns:
            FilePath -- A new object containing the joined path.
        """
        return FilePath(os.path.join(self, *args))

    def dirname(self):
        """Returns the dirname of the current path (using os.path.dirname) as a
        FilePath object.

        Returns:
            FilePath -- the path's directory name.
        """
        return FilePath(os.path.dirname(self))

    def basename(self):
        """Return the basename, i.e. '/path/to/file.ext' -> 'file.ext'

        Returns:
            str -- The final segment of the path.
        """
        return os.path.basename(self)

    def isWritable(self):
        """Checks if the path is writable. The Write and Execute bits must
        be enabled.

        Returns:
            bool -- True is writable
        """
        return os.access(self, os.W_OK | os.X_OK)

# functions -------------------------------------------------------------------

def readJson(fpath):
    """Read a json file without exception handling.

    Arguments:
        fpath {str} -- full path to json file

    Returns:
        dict -- json data
    """
    with open(fpath, 'r') as fhdl:
        data = json.load(fhdl)
    return data


def setup_environment(jsonDict):
    """make sure that RMANTREE and RMSTREE are defined in our environment and
    we can import our python module.

    Arguments:
        jsonDict {dict} -- json data

    Returns:
        tuple -- (rmanAssets, rman_version)
    """
    rmantree = FilePath(jsonDict['RMANTREE'])
    rmstree = FilePath(jsonDict['RMSTREE'])

    if not rmantree in os.environ:
        os.environ['RMANTREE'] = rmantree.osPath()
    if not rmstree in os.environ:
        os.environ['RMSTREE'] = rmstree.osPath()

    rman_version = float(re.search(r'RenderManProServer-(\d+\.\d+)', rmantree).group(1))

    rmstree_py = rmstree.join(rmstree, "scripts")
    if int(rman_version) == 21:
        if rmstree_py not in sys.path:
            sys.path.append(rmstree_py)
    else:
        rmantree_py = rmantree.join(rmantree, "bin")
        if rmstree_py not in sys.path:
            sys.path.insert(0, rmstree_py)
        if rmantree_py not in sys.path:
            sys.path.insert(0, rmantree_py)
    return rman_version


def set_params(settings_dict, chan, node_name, asset):
    # The bxdf may need specific settings to match Substance Painter
    try:
        params = settings_dict[chan]
    except (KeyError, TypeError):
        pass
    else:
        for pname, pdict in params.iteritems():
            asset.addParam(node_name, pname, pdict)
            DBUG('       |_ param: %s %s = %s', pdict['type'], pname, pdict['value'])


def add_texture_node(asset, node_name, ntype, filepath):
    asset.addNode(node_name, ntype, 'pattern', ntype)
    pdict = {'type': 'string', 'value': filepath}
    asset.addParam(node_name, 'filename', pdict)
    if '_MAPID_' in filepath:
        asset.addParam(node_name, 'atlasStyle', {'type': 'int', 'value': 1})


def set_metadata(asset, mat_dict):
    meta = asset.stdMetadata()
    meta['author'] = getpass.getuser()
    meta['description'] = 'Created by RenderMan for Substance Painter 0.3.0'
    meta['resolution'] = '%d x %d' % (mat_dict['resolution'][0],
                                      mat_dict['resolution'][1])
    for k, v in meta.iteritems():
        asset.addMetadata(k, v)


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


def app(name):
    if os.name is 'nt':
        return (name + '.exe')
    return name


def convert_to_aces(asset_path, fpath_list):
    for img in fpath_list:
        cmd = ['%s/bin/oiiotool' % os.getenv('REZ_OIIO_ROOT')]
        cmd += [img, '-v', '--runstats', '--info', '--iscolorspace', 'srgb_texture'] # how to determine if channel is color or not?
        cmd += ['--tocolorspace', 'acescg', '-o', img] #not sure oiiotool allows overwrite?


def txmake(is_udim, asset_path, fpath_list):

    rmantree = FilePath(os.environ['RMANTREE'])
    binary = rmantree.join('bin', app('txmake')).osPath()
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
        cmd[-2] = FilePath(img).osPath()
        dirname, filename = os.path.split(img)
        texfile = os.path.splitext(filename)[0] + '.tex'
        cmd[-1] = asset_path.join(texfile).osPath()
        DBUG('       |_ txmake : %s -> %s', cmd[-2], cmd[-1])
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             startupinfo=startupInfo())
        p.wait()

    # return a local path to the tex file.
    dirname, filename = os.path.split(fpath_list[0])
    fname, fext = os.path.splitext(filename)
    asset_file_ref = FilePath(dirname).join(fname + '.tex')
    if is_udim:
        asset_file_ref = re.sub(r'1\d{3}', '_MAPID_', asset_file_ref)
    return asset_file_ref


def export():
    """Export a RenderManAsset package based on  a json file.
    """
    INFO('Start !')

    if len(sys.argv) < 2:
        ERR('expecting 2 arguments !')
        raise Exception

    # get the input json file
    jsonFile = FilePath(sys.argv[1].replace('"', ''))

    # import json file
    jsonDict = readJson(jsonFile)
    DBUG('OK: json read')

    rman_version = setup_environment(jsonDict)
    if int(rman_version) >= 22:
        import rmanAssets.core as ra         # pylint: disable=import-error
    else:
        import rfm.rmanAssets as ra     # pylint: disable=import-error
    DBUG('OK: imported rmanAssets')

    # constants
    _bump = ('height', 'normal')
    slotsFile = FilePath(os.path.dirname(os.path.realpath(__file__))).join('rules.json')
    rules = readJson(slotsFile)
    DBUG('OK: rules read')

    _bxdf = jsonDict['bxdf']
    bxdf_rules = rules[_bxdf]
    mappings = bxdf_rules['mapping']
    graph = bxdf_rules.get('graph', None)
    settings = bxdf_rules.get('settings', None)
    is_udim = jsonDict['udim']

    # we save the assets to SP's export directory, because we know it is writable.
    # We will move them to the requested location later.
    exportPath = jsonFile.dirname()

    # build assets
    assetList = []
    scene = jsonDict['scene']
    matArray = jsonDict['document']
    for mat in matArray:
        label = scene
        if not is_udim:
            label = '%s_%s' % (scene, mat['textureSet'])
        chans = mat['channels']
        DBUG('+ Exporting %s', label)

        assetPath = exportPath.join(label + '.rma')
        DBUG('  + assetPath %s', assetPath)
        assetJsonPath = assetPath.join('asset.json')
        DBUG('  + assetJsonPath %s', assetJsonPath)

        # create asset directory
        if not assetPath.exists():
            try:
                os.mkdir(assetPath.osPath())
            except (OSError, IOError):
                XCPT('Asset directory could not be created !')
                sys.exit(0)
            DBUG('  + Created dir: %s', assetPath)
        else:
            DBUG('  + dir exists: %s', assetPath)

        # create asset
        try:
            asset = ra.RmanAsset(assetType='nodeGraph', label=label)
        except Exception:
            XCPT('Asset creation failed')
            sys.exit(0)

        # create standard metadata
        #
        set_metadata(asset, mat)

        # Compatibility data
        # This will help other application decide if they can use this asset.
        #
        prmanVersion = str(rman_version)
        asset.setCompatibility(hostName='Substance Painter',
                               hostVersion=jsonDict['sp_version'],
                               rendererVersion=prmanVersion)
        DBUG('  + compatibility set')

        # create nodes
        # start by adding a root node
        #
        rootNode = label + '_Material'
        asset.addNode(rootNode, 'shadingEngine', 'root', 'shadingEngine')
        pdict = {'type': 'reference float[]', 'value': None}
        asset.addParam(rootNode, 'surfaceShader', pdict)
        DBUG('  + Root node: %s', rootNode)

        # add a disney or pixar bxdf
        #
        bxdfNode = label + "_Srf"
        asset.addNode(bxdfNode, _bxdf, 'bxdf', _bxdf)
        DBUG('  + BxDF node: %s  (%s)', (rootNode, _bxdf))

        # The bxdf may need specific settings to match Substance Painter
        set_params(settings, 'bxdf', bxdfNode, asset)

        # connect surf to root node
        #
        asset.addConnection('%s.outColor' % bxdfNode,
                            '%s.surfaceShader' % rootNode)

        # build additional nodes if need be.
        #
        if graph:
            DBUG('  + Create graph nodes...')
            for nname, ndict in graph['nodes'].iteritems():
                lname = label + nname
                asset.addNode(lname, ndict['nodetype'],
                              'pattern', ndict['nodetype'])
                DBUG('    |_ %s  (%s)' % (lname, ndict['nodetype']))
                if 'params' in ndict:
                    for pname, pdict in ndict['params'].iteritems():
                        asset.addParam(lname, pname, pdict)
                        DBUG('       |_ param: %s %s = %s' %
                             (pdict['type'], pname, pdict['value']))

        # create texture nodes
        DBUG('  + Create texture nodes...')
        chanNodes = {}
        for chan, fpath_list in chans.iteritems():
            nodeName = "%s_%s_tex" % (label, chan)
            DBUG('    |_ %s' % nodeName)
            chanNodes[chan] = nodeName
            convert_to_aces(assetPath, fpath_list)
            fpath = txmake(is_udim, assetPath, fpath_list)

            # for aces conversion, only apply to color images.  how?
            if chan == 'normal':
                add_texture_node(asset, nodeName, 'PxrNormalMap', fpath)
            elif chan == 'height':
                add_texture_node(asset, nodeName, 'PxrBump', fpath)
            else:
                add_texture_node(asset, nodeName, 'PxrTexture', fpath)
            set_params(settings, chan, nodeName, asset)

        # make direct connections
        #
        DBUG('  + Direct connections...')
        for chan in chans:
            src = None
            dstType = mappings[chan]['type']
            dstParam = mappings[chan]['param']
            if dstType == 'normal':
                src = '%s.resultN' % (chanNodes[chan])
            elif dstType == 'color':
                src = '%s.resultRGB' % (chanNodes[chan])
            elif dstType == 'float':
                src = '%s.resultR' % (chanNodes[chan])
            else:
                # don't create a connection
                if dstParam != 'graph':
                    # connections with a graph type will be handled later, so
                    # we don't warn in that case.
                    print 'WARNING: Not connecting: %s' % chan
                continue
            if dstParam == 'graph':
                continue
            dst = '%s.%s' % (bxdfNode, dstParam)
            asset.addConnection(src, dst)
            DBUG('    |_ connect: %s -> %s' % (src, dst))
            # also tag the bxdf param as connected
            pdict = {'type': 'reference ' + dstType, 'value': None}
            asset.addParam(bxdfNode, dstParam, pdict)
            DBUG('       |_ param: %s %s -> %s' % (pdict['type'],
                                                   dstParam,
                                                   pdict['value']))

        # make graph connections
        #
        if graph:
            if 'connections' in graph:
                DBUG('  + Connect graph nodes...')
                for con in graph['connections']:

                    src_node = con['src']['node']
                    src_ch = None
                    if src_node == _bxdf:
                        src_node = bxdfNode
                    elif src_node.startswith('ch:'):
                        src_ch = src_node[3:]
                        if src_ch in chanNodes:
                            src_node = chanNodes[src_ch]
                        else:
                            continue
                    if not src_node.startswith(label):
                        src_node = label + src_node
                    src = '%s.%s' % (src_node, con['src']['param'])

                    dst_node = con['dst']['node']
                    dst_ch = None
                    if dst_node == _bxdf:
                        dst_node = bxdfNode
                    elif dst_node.startswith('ch:'):
                        dst_ch = dst_node[3:]
                        if dst_ch in chanNodes:
                            dst_node = chanNodes[dst_ch]
                        else:
                            continue
                    if not dst_node.startswith(label):
                        dst_node = label + dst_node
                    dst = '%s.%s' % (dst_node, con['dst']['param'])
                    asset.addConnection(src, dst)
                    DBUG('    |_ connect: %s -> %s' % (src, dst))
                    # mark param as a connected
                    dstType = con['dst']['type']
                    pdict = {'type': 'reference %s' % dstType, 'value': None}
                    asset.addParam(dst_node, con['dst']['param'], pdict)
                    DBUG('       |_ param: %s %s = %s' % (pdict['type'],
                                                          con['dst']['param'],
                                                          pdict['value']))

        # save asset
        #
        DBUG('  + ready to save: %s' % assetJsonPath)
        try:
            asset.save(assetJsonPath, False)
        except:
            XCPT('Saving the asset failed !')
            raise

        # mark this asset as ready to be moved
        #
        assetList.append(assetPath)

    # move assets to the requested location
    #
    dst = jsonDict['saveTo']
    for item in assetList:
        # if the asset already exists in the destination
        # location, we need to move it first.
        dstAsset = os.path.join(dst, os.path.basename(item))
        if os.path.exists(dstAsset):
            try:
                os.rename(dstAsset, dstAsset + '_old')
            except (OSError, IOError):
                XCPT('Could not rename asset to %s_old' % dstAsset)
                continue
            else:
                shutil.rmtree(dstAsset + '_old', ignore_errors=False)
        try:
            shutil.move(item, dst)
        except (OSError, IOError):
            XCPT('WARNING: Could not copy asset to %s' % dst)


    # clean-up intermediate files
    for mat in matArray:
        for chan, fpath_list in chans.iteritems():
            for fpath in fpath_list:
                if not os.path.exists(fpath):
                    print 'cleanup: file not found: %s' % fpath
                    continue
                try:
                    os.remove(fpath)
                except (OSError, IOError):
                    XCPT('Cleanup failed: %s' % fpath)
                else:
                    DBUG('Cleanup: %s' % fpath)

    if os.path.exists(jsonFile):
        try:
            os.remove(jsonFile)
        except (OSError, IOError):
            XCPT('Cleanup failed: %s' % jsonFile)
        else:
            DBUG('Cleanup: %s' % jsonFile)

    INFO('RenderMan : Done !')


# main

try:
    export()
except Exception:
    XCPT('Export failed')
sys.exit(0)
