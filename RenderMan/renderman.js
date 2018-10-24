// ----------------------------------------------------------------------------
// MIT License
//
// Copyright (c) 2016 Philippe Leprince
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.
// ----------------------------------------------------------------------------


function osPath(input_path) {
    var platformPath = input_path
    if (Qt.platform.os == "windows") {
        var tmp = new String(platformPath)
        platformPath = tmp.replace(/\//g, "\\")
        // alg.log.info("[WIN] platformPath = " + platformPath)
    }
    return platformPath
}


function jsonPath(input_path) {
    var jsnPath = input_path
    if (Qt.platform.os == "windows") {
        var tmp = new String(jsnPath)
        jsnPath = tmp.replace(/\\/g, "\\\\")
        // alg.log.info("[WIN] jsnPath = " + jsnPath)
    }
    return jsnPath
}


function checkPrefs() {
    var all_valid = true
    if (alg.settings.value("RMANTREE") == undefined) {
        all_valid = false
        alg.log.warn("RMANTREE = " + alg.settings.value("RMANTREE"))
    }
    if (alg.settings.value("RMSTREE") == undefined) {
        all_valid = false
        alg.log.warn("RMSTREE = " + alg.settings.value("RMSTREE"))
    }
    if (alg.settings.value("saveTo") == undefined) {
        all_valid = false
        alg.log.warn("saveTo = " + alg.settings.value("saveTo"))
    }
    return all_valid
}


function isUDIMProject(document)
{
    var isUDIM = true
    var udimPat = '1[0-9]{3}'
    for (var matIdx = 0; matIdx < document.materials.length; matIdx++)
    {
        if (document.materials[matIdx].name.match(udimPat) == null)
        {
            isUDIM = false
            break
        }
    }
    alg.log.info('UDIM = ' + isUDIM)
    return isUDIM
}


// FIXME: the bxdf param is currently ignored.

function exportAssets(bxdf) {

    // bail out if the prefs are not all filled
    //
    var valid = checkPrefs()
    if (!valid) {
        alg.log.error("RenderMan: Please open the configure panel and fill all fields !")
        return
    }

    alg.log.info("\n\n\n\n")
    var toks = alg.project.url().split('/')
    var scene_name = toks[toks.length - 1]
    scene_name = scene_name.split(".")[0]
    alg.log.info("Scene name: " + scene_name)

    // Some useful variables
    //
    var sep = "/"
    var pyBin = "python"
    var winOS = (Qt.platform.os == "windows")
    if (winOS) {
        sep = "\\"
        pyBin += ".exe"
    }
    var ext = ".png"
    var script = "rmanAssetsSubstancePainter.py"
    var exportPath = ""
    var jsonFilePath = ""
    var tab = "    "
    var tab2 = tab + tab
    var tab3 = tab2 + tab
    var tab4 = tab3 + tab

    // Query export path
    //
    exportPath = osPath(alg.mapexport.exportPath())
    exportPath += sep + "RenderMan" + sep
    jsonFilePath = exportPath + "RmanExport.json"

    // Export masks
    //
    var matIdx = 0
    var channelIdx = 0
    var document = alg.mapexport.documentStructure()

    // check if this is a UDIM set
    var isUDIM = isUDIMProject(document)

    // store env vars
    //
    var obj = {
        scene: scene_name,
        sp_version: alg.version.painter,
        RMANTREE: jsonPath(alg.settings.value("RMANTREE")),
        RMSTREE: jsonPath(alg.settings.value("RMSTREE")),
        bxdf: bxdf,
        udim: isUDIM,
        saveTo: jsonPath(alg.settings.value("saveTo")),
        document: []
    }

    // Parse all materials (texture sets)
    //
    var mobj = null
    for (matIdx = 0; matIdx < document.materials.length; matIdx++)
    {
        var material = document.materials[matIdx].name
        if (!isUDIM || matIdx == 0)
        {
            mobj = {
                textureSet: isUDIM ? "UDIM" : material,
                resolution: alg.mapexport.textureSetResolution(material),
                channels: {}
            }
        }

        var numChannels = document.materials[matIdx].stacks[0].channels.length
        for (channelIdx = 0; channelIdx < numChannels; channelIdx++)
        {
            var thisChannel = document.materials[matIdx].stacks[0].channels[channelIdx]
            // alg.log.info("RenderMan:   | " + thisChannel)

            // Skip the height channel: we prefer normal maps.
            if (thisChannel == "height")
            {
                // alg.log.info("RenderMan:   |_ skip")
                continue
            }

            var output = exportPath
            if (isUDIM)
                output += thisChannel + "." + material + ext
            else
                output += material + "_" + thisChannel + ext

            var t0 = new Date().getTime()
            if (thisChannel == "normal")
            {
                // Make sure the normals are correctly configured to combine
                // mesh + height + normal.
                alg.mapexport.saveConvertedMap([material], "normal_directx", output)
            }
            else
            {
                // regular map export
                alg.mapexport.save([material, thisChannel], output)
            }
            var t1 = new Date().getTime()
            alg.log.info("RenderMan:   |_ Exported in " + ((t1-t0)/1000.0).toFixed(2) + " sec.: " + output)

            try {
                mobj.channels[thisChannel].push(jsonPath(output))
            } catch (error) {
                mobj.channels[thisChannel] = [jsonPath(output)]
            }
        }

        if (!isUDIM || matIdx == 0)
        {
            obj.document.push(mobj)
        }
    }

    // Write json file and export
    //
    if (obj != null)
    {
        alg.log.info("RenderMan: Writing " + jsonFilePath + "...")

        // write json file needed by the python script
        //
        var jsonFile = alg.fileIO.open(jsonFilePath, "w")
        jsonFile.write(JSON.stringify(obj, null, 4))
        jsonFile.close()

        // Call python
        // FIXME: we should probably just catch exceptions and print the log
        // on error.
        //
        alg.log.info("RenderMan: Launching " + script + "...")
        try
        {
            var fpath = "\"" + jsonFilePath + "\""
            var result = alg.subprocess.check_output([pyBin, script, fpath])
            var lines = result.split(/[\r\n]+/g)
            for (var i in lines)
            {
                alg.log.info("RenderMan:          " + lines[i])
            }
        }
        catch (err)
        {
            alg.log.error('ERROR: ' + err)
        }
    }
    else {
        alg.log.error("RenderMan: Nothing to export !")
    }
    alg.log.info("RenderMan: Export successful ! :)")
}

