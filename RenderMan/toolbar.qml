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
    spacing: 2

    Button
    {
        id: disney
        antialiasing: true
        tooltip: "Export as a PxrDisney Material Preset"
        width: 30
        height: 30

        style: ButtonStyle {
            background: Rectangle {
                width: 30
                height: 30

                Image {
                    source: "icons/PxrDisney.png"
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
        width: 30
        height: 30

        style: ButtonStyle {
            background: Rectangle {
                width: 30
                height: 30

                Image {
                    source: "icons/PxrSurface.png"
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