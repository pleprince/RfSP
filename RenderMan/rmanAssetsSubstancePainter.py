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


# python 2.7 plugin for substance painter 2.3+

# pylint: disable=import-error
# pylint: disable=global-statement
# pylint: disable=invalid-name
# pylint: disable=bare-except

# standard imports first
import os
import os.path
import sys
import json
import re
# import platform
from time import gmtime, strftime
import traceback
import shutil

thisDir = os.path.dirname(os.path.realpath(__file__))
_logfile = None


# functions -------------------------------------------------------------------


def msg(s):
    global _logfile
    if _logfile is None:
        log = os.path.join(thisDir, 'log.txt')
        # print '>> %s\n' % log
        _logfile = open(log, 'w')
        timestamp = strftime("%a, %d %b %Y %H:%M:%S", gmtime())
        _logfile.write(timestamp + '\n')
        _logfile.write(log + '\n')
        _logfile.write('-----------------------\n')
    # sys.stdout.write(s + '\n')
    # sys.stdout.flush()
    _logfile.write(s + '\n')
    _logfile.flush()


def err():
    try:
        msg('  err: ' + str(sys.exc_info()[0]))
    except:
        pass
    try:
        msg('     : ' + str(sys.exc_info()[1]))
    except:
        pass
    try:
        traceback.print_exc(file=_logfile)
    except:
        pass


def onExit():
    global _logfile
    if _logfile is not None:
        _logfile.write('Exit.\n')
        _logfile.close()


def exitWithError():
    # global thisDir
    print 'An error occured.'
    print 'Check the log file: %s' % (os.path.join(thisDir, 'log.txt'))
    onExit()
    sys.exit(0)


def exitWithSuccess():
    onExit()
    sys.exit(0)


def readJson(fpath):
    fh = open(fpath, 'r')
    data = json.load(fh)
    fh.close()
    return data


def export():
    msg('Start !')

    if len(sys.argv) < 2:
        msg('ERROR: expecting 2 arguments !')
        raise Exception

    # get the input json file
    #
    jsonFile = sys.argv[1].replace('"', '')

    # import json file
    #
    jsonDict = readJson(jsonFile)
    msg('OK: json read')

    # make sure that:
    # - RMANTREE and RMSTREE are defined in our environment
    # - we can import our python module
    #
    rmantree = jsonDict['RMANTREE']
    rmstree = jsonDict['RMSTREE']

    if not rmantree in os.environ:
        os.environ['RMANTREE'] = rmantree
    if not rmstree in os.environ:
        os.environ['RMSTREE'] = rmstree

    rmstree_py = os.path.join(rmstree, "scripts")
    if rmstree_py not in sys.path:
        sys.path.append(rmstree_py)

    # now import our module
    #
    try:
        import rfm.rmanAssets as ra
    except:
        err()
        msg('ERROR: failed to import rfm.rmanAssets')
        msg('sys.path : %s' % str(sys.path).replace(',', '\n'))
        raise Exception
    msg('OK: imported rfm.rmanAssets')

    # constants
    #
    _bump = ['height', 'normal']
    slotsFile = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'rules.json')
    _rules = readJson(slotsFile)
    msg('OK: rules read')

    _bxdf = jsonDict['bxdf']

    # we save the assets to SP's export directory, because we know it is writable.
    # We will move them to the requested location later.
    #
    exportPath = os.path.dirname(jsonFile)

    # build assets
    #
    assetList = []
    matArray = jsonDict['document']
    for mat in matArray:
        label = mat['textureSet']
        label = 'sp_' + label
        chans = mat['channels']
        msg('+ Exporting %s' % label)

        assetPath = os.path.join(exportPath, label + '.rma')
        msg('  + assetPath %s' % assetPath)
        assetJsonPath = os.path.join(assetPath, 'asset.json')
        msg('  + assetJsonPath %s' % assetJsonPath)

        # create asset directory
        if not os.path.exists(assetPath):
            try:
                os.mkdir(assetPath)
            except:
                err()
                onExit()
                sys.exit(0)
            msg('  + Created dir: %s' % assetPath)
        else:
            msg('  + dir exists: %s' % assetPath)

        # create asset
        try:
            Asset = ra.RmanAsset(assetType='nodeGraph', label=label)
        except:
            err()
            onExit()
            sys.exit(0)

        # create standard metadata
        #
        meta = Asset.stdMetadata()
        for k, v in meta.iteritems():
            Asset.addMetadata(k, v)

        # Compatibility data
        # This will help other application decide if they can use this asset.
        # FIXME: versions are hard-coded.
        #
        prmanVersion = '21.3'
        Asset.setCompatibility(hostName='Substance Painter',
                               hostVersion='2.4',
                               rendererVersion=prmanVersion)
        msg('  + compatibility set')

        # create nodes
        # start by adding a root node
        #
        rootNode = label + '_Material'
        Asset.addNode(rootNode, 'shadingEngine', 'root', 'shadingEngine')
        pdict = {'type': 'reference float[]', 'value': None}
        Asset.addParam(rootNode, 'surfaceShader', pdict)
        msg('  + Root node: %s' % rootNode)

        # add a disney or pixar bxdf
        #
        bxdfNode = label + "_Srf"
        Asset.addNode(bxdfNode, _bxdf, 'bxdf', _bxdf)
        msg('  + BxDF node: %s  (%s)' % (rootNode, _bxdf))

        # connect surf to root node
        #
        Asset.addConnection('%s.outColor' % bxdfNode,
                            '%s.surfaceShader' % rootNode)

        # build additional nodes if need be.
        #
        if 'graph' in _rules[_bxdf]:
            msg('  + Create graph nodes...')
            for nname, ndict in _rules[_bxdf]['graph']['nodes'].iteritems():
                lname = label + nname
                Asset.addNode(lname, ndict['nodetype'],
                              'pattern', ndict['nodetype'])
                msg('    |_ %s  (%s)' % (lname, ndict['nodetype']))
                if 'params' in ndict:
                    for pname, pdict in ndict['params'].iteritems():
                        Asset.addParam(lname, pname, pdict)
                        msg('       |_ param: %s %s = %s' %
                            (pdict['type'], pname, pdict['value']))

        # create texture nodes
        msg('  + Create texture nodes...')
        chanNodes = {}
        for ch, fpath in chans.iteritems():
            nodeName = "%s_%s_tex" % (label, ch)
            chanNodes[ch] = nodeName
            if ch not in _bump:
                Asset.addNode(nodeName, 'PxrTexture', 'pattern', 'PxrTexture')
                pdict = {'type': 'string', 'value': fpath}
                Asset.addParam(nodeName, 'filename', pdict)
                pdict = {'type': 'int', 'value': 1}
                Asset.addParam(nodeName, 'linearize', pdict)
            else:
                if ch == 'normal':
                    Asset.addNode(nodeName, 'PxrNormalMap',
                                  'pattern', 'PxrNormalMap')
                    pdict = {'type': 'string', 'value': fpath}
                    Asset.addParam(nodeName, 'filename', pdict)
                    pdict = {'type': 'float', 'value': 1.0}
                    Asset.addParam(nodeName, 'adjustAmount', pdict)
                elif ch == 'height':
                    Asset.addNode(nodeName, 'PxrBump', 'pattern', 'PxrBump')
                    pdict = {'type': 'string', 'value': fpath}
                    Asset.addParam(nodeName, 'filename', pdict)
                    pdict = {'type': 'float', 'value': 1.0}
                    Asset.addParam(nodeName, 'adjustAmount', pdict)
                else:
                    msg('    ! wow: %s' % ch)
            msg('    |_ %s' % nodeName)

        # make direct connections
        #
        msg('  + Direct connections...')
        for ch in chans:
            src = None
            dstType = _rules[_bxdf]['mapping'][ch]['type']
            dstParam = _rules[_bxdf]['mapping'][ch]['param']
            if dstType == 'normal':
                src = '%s.resultN' % (chanNodes[ch])
            elif dstType == 'color':
                src = '%s.resultRGB' % (chanNodes[ch])
            elif dstType == 'float':
                src = '%s.resultR' % (chanNodes[ch])
            else:
                # don't create a connection
                if dstParam != 'graph':
                    # connections with a graph type will be handled later, so
                    # we don't warn in that case.
                    print 'WARNING: Not connecting: %s' % ch
                continue
            if dstParam == 'graph':
                continue
            dst = '%s.%s' % (bxdfNode, dstParam)
            Asset.addConnection(src, dst)
            msg('    |_ connect: %s -> %s' % (src, dst))
            # also tag the bxdf param as connected
            pdict = {'type': 'reference ' + dstType, 'value': None}
            Asset.addParam(bxdfNode, dstParam, pdict)
            msg('       |_ param: %s %s -> %s' % (pdict['type'],
                                                  dstParam,
                                                  pdict['value']))

        # make graph connections
        #
        if 'graph' in _rules[_bxdf]:
            if 'connections' in _rules[_bxdf]['graph']:
                msg('  + Connect graph nodes...')
                for con in _rules[_bxdf]['graph']['connections']:

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
                    Asset.addConnection(src, dst)
                    msg('    |_ connect: %s -> %s' % (src, dst))
                    # mark param as a connected
                    dstType = con['dst']['type']
                    pdict = {'type': 'reference %s' % dstType, 'value': None}
                    Asset.addParam(dst_node, con['dst']['param'], pdict)
                    msg('       |_ param: %s %s = %s' % (pdict['type'],
                                                         con['dst']['param'],
                                                         pdict['value']))

        # save asset
        #
        msg('  + ready to save: %s' % assetJsonPath)
        try:
            Asset.save(assetJsonPath, False)
        except:
            err()
            raise Exception

        # mark this asset as ready to be moved
        #
        assetList.append(assetPath)

    # move assets to the requested location
    #
    dst = jsonDict['saveTo']
    for asset in assetList:
        # if the asset already exists in the destination
        # location, we need to move it first.
        dstAsset = os.path.join(dst, os.path.basename(asset))
        if os.path.exists(dstAsset):
            try:
                os.rename(dstAsset, dstAsset + '_old')
            except:
                msg('WARNING: Could not rename asset to %s_old' % dstAsset)
                err()
                continue
            else:
                shutil.rmtree(dstAsset + '_old', ignore_errors=False)
        try:
            shutil.move(asset, dst)
        except:
            msg('WARNING: Could not copy asset to %s' % dst)
            err()

    # clean-up intermediate files
    if True:
        for mat in matArray:
            for ch, fpath in chans.iteritems():
                if not os.path.exists(fpath):
                    print 'cleanup: file not found: %s' % fpath
                    continue
                try:
                    os.remove(fpath)
                except:
                    msg('Cleanup failed: %s' % fpath)
                    err()
                else:
                    msg('Cleanup: %s' % fpath)

        if os.path.exists(jsonFile):
            try:
                os.remove(jsonFile)
            except:
                msg('Cleanup failed: %s' % jsonFile)
                err()
            else:
                msg('Cleanup: %s' % jsonFile)
    else:
        msg('skipped cleanup')

    msg('RenderMan : Done !')


# main

try:
    export()
except:
    err()
    exitWithError()
else:
    exitWithSuccess()
