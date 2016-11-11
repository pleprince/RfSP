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

# standard imports first
import os
import os.path
import sys
import json
import platform
from time import gmtime, strftime
import traceback
import shutil

thisDir = os.path.dirname(os.path.realpath(__file__))
_logfile = None


# functions -------------------------------------------------------------------


def msg(s):
    global _logfile
    global thisDir
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
    global _logfile
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
    global thisDir
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
    if not rmstree_py in sys.path:
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
    slotsFile = os.path.join(os.path.dirname(
        os.path.realpath(__file__)), 'rules.json')
    _rules = readJson(slotsFile)
    msg('OK: rules read')

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

        # Compatibility data
        # This will help other application decide if they can use this asset.
        # FIXME: versions are hard-coded.
        #
        prmanVersion = '21.2'
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
                    print 'wow: %s' % ch

        # add a disney bxdf
        #
        bxdfNode = label + "_Srf"
        Asset.addNode(bxdfNode, 'PxrDisney', 'bxdf', 'PxrDisney')

        # make connections
        #
        for ch in chans:
            src = None
            dstType = _rules['PxrDisney'][ch]['type']
            dstParam = _rules['PxrDisney'][ch]['name']
            if dstType == 'normal':
                src = '%s.resultN' % (chanNodes[ch])
            elif dstType == 'color':
                src = '%s.resultRGB' % (chanNodes[ch])
            elif dstType == 'float':
                src = '%s.resultR' % (chanNodes[ch])
            else:
                # don't create a connection
                print 'WARNING: Not connecting: %s' % ch
                continue
            dst = '%s.%s' % (bxdfNode, dstParam)
            Asset.addConnection(src, dst)

            # also tag the bxdf param as connected
            #
            pdict = {'type': 'reference ' + dstType, 'value': None}
            Asset.addParam(bxdfNode, dstParam, pdict)

        # connect surf to root node
        #
        Asset.addConnection('%s.outColor' %
                            bxdfNode, '%s.surfaceShader' % rootNode)

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
    if False:
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

try:
    export()
except:
    err()
    exitWithError()
else:
    exitWithSuccess()
