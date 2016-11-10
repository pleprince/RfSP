
function exportAssets(bxdf) {
    // Some useful variables
    //
    var sep = "/"
    var pyBin = "python"
    if (Qt.platform.os == "windows") {
        sep = "\\"
        pyBin += ".exe"
    }
    var ext = ".png"
    // var pluginPath = "/Users/plp/src/allegorithmic/RenderMan" + sep
    var pluginPath = ""
    var script = pluginPath + "rmanAssetsSubstancePainter.py"
    var exportPath = ""
    var jsonFilePath = ""
    var tab = "    "

    // Query export path
    //
    exportPath = alg.mapexport.exportPath() + sep + "RenderMan" + sep
    jsonFilePath = exportPath + "RmanExport.json"

    // Export masks
    //
    var matIdx = 0
    var channelIdx = 0;
    var document = alg.mapexport.documentStructure()
    var fileContent = "[\n"

    // alg.log.info("rman: -----------------------------------")

    // Parse all materials (texture sets)
    //
    for (matIdx = 0; matIdx < document.materials.length; matIdx++) {
        var material = document.materials[matIdx].name
        fileContent += tab + "{\n"
        fileContent += tab + tab + "\"material\": \"" + material + "\",\n"
        fileContent += tab + tab + "\"channels\": {\n"
        // alg.log.info("rman: Texture Set \"" + material + "\" : ")

        var numChannels = document.materials[matIdx].stacks[0].channels.length
        for (channelIdx = 0; channelIdx < numChannels; channelIdx++) {
            var thisChannel = document.materials[matIdx].stacks[0].channels[channelIdx]
            // alg.log.info("rman:   | " + thisChannel)

            // var Stack = document.materials[ setIndex ].stacks[0].name
            var output = exportPath + material + "_" + thisChannel + ext

            var materials = []
            materials[0] = material
            materials[1] = thisChannel

            alg.mapexport.save(materials, output)
            // alg.log.info("rman:   |_ Exported : " + output)

            //Prepare Data for text file
            fileContent += tab + tab + tab + "\"" + thisChannel + "\": \"" + output + "\""
            if (channelIdx < numChannels - 1)
                fileContent += ",\n"
            else
                fileContent += "\n"
        }
        if (matIdx < document.materials.length - 1)
            fileContent += tab + tab + "}\n" + tab + "},\n"
        else
            fileContent += tab + tab + "}\n" + tab + "}\n"
    }
    fileContent += "]\n"

    //
    if (fileContent.length > 0) {
        // alg.log.info("rman: Writing " + jsonFilePath + "...")

        //-----------------------------------------------
        //Save data for Python and Batch tools
        //-----------------------------------------------
        var jsonFile = alg.fileIO.open(jsonFilePath, "w")
        jsonFile.write(fileContent)
        jsonFile.close()

        //-----------------------------------------------
        //Packing (call Python)
        //-----------------------------------------------
        //Call python
        var rmantree = "\"" + alg.settings.value("RMANTREE") + "\""
        var rmstree = "\"" + alg.settings.value("RMSTREE") + "\""
        var fpath = "\"" + jsonFilePath + "\""
        var result = alg.subprocess.check_output([pyBin, script, rmantree, rmstree, fpath])

        alg.log.info("rman: Python : " + result)
    }
    else {
        alg.log.error("rman: Nothing to export !")
    }
    alg.log.info("rman: Done")
}