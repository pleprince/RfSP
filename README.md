# RfSP

## RenderMan for Substance Painter 2.x

This plugin exports your [Substance Painter](https://www.allegorithmic.com/products/substance-painter) project as one or more RenderManAsset.

RenderManAsset is the format used by the preset browser that was introduced in [RenderMan For Maya](https://rmanwiki.pixar.com/display/REN/RenderMan+for+Maya) 21.0. It allows for easy material setup interchange and includes dependencies like textures or OSL shaders.

[demo video of 0.1.1](img/RfSP_v0.1.1.mp4)

## Features

### ![Alt](RenderMan/icons/PxrDisney.png "PxrDisney") : Export to PxrDisney-based material

The asset will use the PxrDisney bxdf to re-create the Substance Painter material. There are limitations though:

* The Substance Painter project MUST use the pbr-metal-rough shader.
* Opacity is not supported by PxrDisney.

### ![Alt](RenderMan/icons/PxrSurface.png "PxrSurface") : Export to PxrSurface-based material

This is not implemented yet.

## Requirements

This plugin will NOT work without the following software:

* Substance Painter 2.3+
* RenderMan Pro Server 21.0+
* RenderMan For Maya 21.0+
* [Python 2.7+](https://www.python.org/downloads/release/python-2712/) (but not Python 3.x)

## Install

* Download a zip archive from the github page
* Un-zip the archive
* Copy the RenderMan folder inside Substance Painter's plugin folder.
  > OSX: `/Users/yourlogin/Documents/Substance Painter 2/plugins`

## Known Issues

* No progress indication during export: be patient !
  * It takes time to export the maps and turn them into textures. The plugin will print a message in the log when done.
* No UDIM support yet.
* Only tested on OSX.

## Usage

1. On first use, open the "configure" dialog.

   ![Alt](img/open_configure_dialog.jpg "open config dialog")

1. Fill ALL fields of the dialog and click "Save", otherwise the export will fail.

   ![Alt](img/configure_dialog.jpg "open config dialog")

1. Once this initial configuration is done, the settings will be remembered even if you close Substance Painter.

1. Open a SP project and click one of the pixar buttons in the shelf.

   Hint: _Only the first one (PxrDisney) works for now._

   ![Alt](img/shelf_buttons.jpg "open config dialog")

## Release notes

### 0.1.0

* Initial Release
* Implemented configure dialog to specify the path to RenderMan Pro Server and RenderMan For Maya. This is necessary because SP uses javascript, a sandboxed language that can not get access to environment variables.
* Export all channels from all textureSets to png files.
* Implemented basic export to PxrDisney-based asset.
  * Each TextureSet will be exported as a RenderManAsset directory.

### 0.1.1

* Added license text to all source files.
