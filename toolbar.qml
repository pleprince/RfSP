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



import QtQuick 2.3
import QtQuick.Window 2.2
import QtQuick.Layouts 1.2
import QtQuick.Controls 1.4
import QtQuick.Controls.Styles 1.4

import "renderman.js" as Renderman

Row
{

    Button
    {
        id: disney
        antialiasing: true
        tooltip: "Export as a PxrDisney Material Preset"
        width: 32
        height: 32

        style: ButtonStyle {
            background: Rectangle {
            implicitWidth: control.width
            implicitHeight: control.height
            width: control.width;
            height: control.height
            color: control.hovered ?
              "#262626" :
              "transparent"

                Image {
                    anchors.fill: parent
                    anchors.margins: 4
                    source: control.hovered && !control.loading ? "icons/PxrDisney_hover.svg" : "icons/PxrDisney_idle.svg"
                    fillMode: Image.PreserveAspectFit
                    width: control.width; height: control.height
                    mipmap: true
                    opacity: 1.0
                }
            }
        }

        onClicked:
        {
            try
            {
            alg.log.info( 'RenderMan: Export PxrDisney-based asset...')
            Renderman.exportAssets('PxrDisney')
            }
            catch(err)
            {
                alg.log.error( 'rman: ' + err.message )
            }
        }
    }


    Button
    {
        id: surface
        antialiasing: true
        tooltip: "Export as a PxrSurface Material Preset"
        width: 32
        height: 32

        style: ButtonStyle {
            background: Rectangle {
            implicitWidth: control.width
            implicitHeight: control.height
            width: control.width;
            height: control.height
            color: control.hovered ?
              "#262626" :
              "transparent"

                Image {
                anchors.fill: parent
                    anchors.margins: 4
                    source: control.hovered && !control.loading ? "icons/PxrSurface_hover.svg" : "icons/PxrSurface_idle.svg"
                    fillMode: Image.PreserveAspectFit
                    width: control.width; height: control.height
                    mipmap: true
                    opacity: 1.0
                }
            }
        }

        onClicked:
        {
            try
            {
                Renderman.exportAssets('PxrSurface')
            }
            catch(err)
            {
                alg.log.error( 'rman: ' + err.message )
            }
        }
    }

}
