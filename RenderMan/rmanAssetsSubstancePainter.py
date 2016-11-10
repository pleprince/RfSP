# python 2.7 plugin for substance painter 2.3+

import os
import os.path
import sys
import json
import platform
from time import gmtime, strftime
import traceback

thisDir = os.path.dirname(os.path.realpath(__file__))
_logfile = None


def msg(s):
    global _logfile
    global thisDir
    if _logfile is None:
        log = os.path.join(thisDir, 'log.txt')
        print '>> %s\n' % log
        _logfile = open(log, 'w')
        timestamp = strftime("%a, %d %b %Y %H:%M:%S", gmtime())
        _logfile.write(timestamp + '\n')
        _logfile.write(log + '\n')
        _logfile.write('-----------------------\n')
    sys.stdout.write(s + '\n')
    sys.stdout.flush()
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
    onExit()
    sys.exit(1)


def exitWithSuccess():
    onExit()
    sys.exit(0)


msg('Start !')


if len(sys.argv) < 4:
    msg('ERROR: expecting 4 arguments !')
    exitWithError()

# get the input json file
#
rmantree = sys.argv[1].replace('"', '')
rmstree = sys.argv[2].replace('"', '')
jsonFile = sys.argv[3].replace('"', '')

if not rmantree in os.environ:
    os.environ['RMANTREE'] = rmantree
if not rmstree in os.environ:
    os.environ['RMSTREE'] = rmantree

rmstree_py = os.path.join(rmstree, "scripts")
if not rmstree_py in sys.path:
    sys.path.append(rmstree_py)

# if jsonFile is None:
#     msg('ERROR: no json file path !')
#     onExit()
#     sys.exit(0)
# else:
#     # jsonFile = os.path.realpath(jsonFile)
#     jsonFile = jsonFile.replace('"', '')
#     msg('OK: json file: %s' % jsonFile)


# import our main module
#
# if os.path.exists(thisDir):
#     if thisDir not in sys.path:
#         sys.path.append(thisDir)
#         msg('OK: added to sys.path: %s' % thisDir)
# # else:
# #     msg('ERROR: path does not exist: %s' % thisDir)
# #     onExit()
# #     sys.exit(0)

# msg('sys.path : %s' % str(sys.path).replace(',', '\n'))

try:
    msg('Trying to import...')
    import rfm.rmanAssets as ra
except:
    err()
    msg('ERROR: failed to import rmanAssets')
    msg('sys.path : %s' % str(sys.path).replace(',', '\n'))
    exitWithSuccess()

msg('OK: imported rmanAssets')


def readJson(fpath):
    fh = open(fpath, 'r')
    data = json.load(fh)
    fh.close()
    return data


# constants
_bump = ['height', 'normal']
slotsFile = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), 'rules.json')
_rules = readJson(slotsFile)
msg('OK: rules read')

# import json file
try:
    matArray = readJson(jsonFile)
except:
    msg('ERROR: json failed: %s' % jsonFile)
    err()
    onExit()
    sys.exit(0)

msg('OK: json read')

exportPath = os.path.dirname(jsonFile)
for mat in matArray:
    label = mat['material']
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
    #
    prmanVersion = '21.2'
    Asset.setCompatibility(hostName='Substance Painter',
                           hostVersion='2.4',
                           rendererVersion=prmanVersion)
    msg('  + compatibility set')

    # create nodes
    # start by adding a root node
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
    bxdfNode = label + "_Srf"
    Asset.addNode(bxdfNode, 'PxrDisney', 'bxdf', 'PxrDisney')

    # make connections
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
        pdict = {'type': 'reference ' + dstType, 'value': None}
        Asset.addParam(bxdfNode, dstParam, pdict)
    # connect surf to root node
    Asset.addConnection('%s.outColor' %
                        bxdfNode, '%s.surfaceShader' % rootNode)

    # save asset
    msg('  + ready to save: %s' % assetJsonPath)
    try:
        Asset.save(assetJsonPath, False)
    except:
        err()
        exitWithSuccess()

# clean-up intermediate files
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

msg('rasp : Done !')
exitWithSuccess()
