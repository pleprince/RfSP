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
                // Renderman.exportAssets('PxrSurface')
                alg.log.error( 'rman: Export to PxrSurface not implemented yet !' )
            }
            catch(err)
            {
                alg.log.error( 'rman: ' + err.message )
            }
        }
    }

}