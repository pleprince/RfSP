# RfSP

## RenderMan for Substance Painter 24.1

This plugin exports your [Substance Painter](https://www.allegorithmic.com/products/substance-painter) project as one or more RenderManAsset.

RenderManAsset is the format used by the preset browser that was introduced in [RenderMan For Maya](https://rmanwiki.pixar.com/display/REN/RenderMan+for+Maya) 21.0. It allows for easy material setup interchange and includes dependencies like textures or OSL shaders.

![demo](img/rfsp.24.1.gif)

## Features

* Open the RenderMan Asset Browser directly in Substance Painter
* Export SP project to LamaSurface, PrxSurface or PxrDisney
* Support the following channels:
  * baseColor
  * metallic
  * roughness
  * normal
  * height
  * emission
  * anisotropylevel
  * anisotropyangle
  * scattering

## Requirements

This plugin will NOT work without the following software:

* Substance Painter 2021.1+, Adobe Substance 3D Painter
* RenderMan Pro Server 24.1+

## Install

* Download a zip archive from the github page
* Un-zip the archive
* Copy the files in the "plugin" folder inside Substance Painter's python plugin folder.
  > OSX: `/Users/yourlogin/Documents/Substance Painter 2/python/plugins`

## Known Issues

* Converted textures' names do not contain the source and destination colorspace.
* When a SP project doesn't define one of the expected channels, SP will issue a warning.
* When multiple assets are created, only the last one gets a preview render.
* The icons of the export dialog are clipped.
* The "import" item of the swatch's contextual menu should be disabled.
