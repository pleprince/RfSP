import QtQuick 2.3
import QtQuick.Window 2.2
import QtQuick.Dialogs 1.2
import QtQuick.Controls 1.4
import QtQuick.Layouts 1.3
import QtQuick.Controls.Styles 1.4


Dialog
{
    signal accepted()
    visible: false
    title: "RenderMan Export Preferences"

    function accept()
    {
        if (rmanPathField.text != "")
        {
            alg.settings.setValue("RMANTREE", rmanPathField.text)
            // alg.log.info("RMANTREE = "+rmanPathField.text)
        }
        if (rmsPathField.text != "")
        {
            alg.settings.setValue("RMSTREE", rmsPathField.text)
            // alg.log.info("RMSTREE = "+rmsPathField.text)
        }
        if (exportPathField.text != "")
        {
            alg.settings.setValue("saveTo", exportPathField.text)
            // alg.log.info("saveTo = "+exportPathField.text)
        }

        accepted()
        close()
    }

    function readPrefs()
    {
        rmanPathField.readPrefs()
        rmsPathField.readPrefs()
        exportPathField.readPrefs()
    }

    FocusScope
    {
        focus: true
        Keys.onPressed: {
            if (event.key === Qt.Key_Escape)
            {
                close()
            }
            else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter)
            {
                accept()
            }
        }
    }

    contentItem: Rectangle
    {
        color: "#292929"
        implicitWidth: 600
        implicitHeight: 180
        anchors.fill: parent
        property var text_color: "#c0c0c0"

        Text
        {
            x:10; y:10
            height: 30
            text: "Please enter the location of RenderMan products."
            color: parent.text_color
            Layout.fillWidth: true
            Layout.fillHeight: true
            // anchors.margins: 10
        }

        RowLayout
        {
            id: rmanlayout
            x:10; y:40
            height: 30
            width: parent.width
            spacing: 6
            Layout.fillWidth: true

            Text
            {
                id: rmanPathLabel
                text: "RenderMan Pro Server:"
                horizontalAlignment: Text.AlignRight
                color: "#e6e6e6"
                Layout.minimumWidth: 150
                Layout.maximumWidth: 150
            }
            RendermanTextField
            {
                id: rmanPathField
                placeholderText: "path to renderman pro server directory"
                anchors.left: rmanPathLabel.right
                anchors.right: rmanPathButton.left
                anchors.leftMargin: 4
                anchors.rightMargin: 4

                function readPrefs()
                {
                    text = alg.settings.value("RMANTREE")
                }

                Component.onCompleted: {
                    readPrefs()
                }

            }
            RendermanButton
            {
                id:rmanPathButton
                text: "pick"
                onClicked: {
                    alg.log.info("rman: click")
                    folderPickerDialog.fieldid = rmanPathField
                    folderPickerDialog.open()
                }
                width: 40
                height: 10
                anchors.right: rmanlayout.right
                anchors.rightMargin: 20
            }
        }

        RowLayout {
            id: rmslayout
            x:10; y:70
            height: 30
            width: parent.width
            spacing: 6
            Layout.fillWidth: true

            Text {
                id: rmsPathLabel
                text: "RenderMan For Maya:"
                horizontalAlignment: Text.AlignRight
                color: "#e6e6e6"
                Layout.minimumWidth: 150
                Layout.maximumWidth: 150
            }
            RendermanTextField {
                id: rmsPathField
                placeholderText: "path to renderman for maya directory"
                anchors.left: rmsPathLabel.right
                anchors.right: rmsPathButton.left
                anchors.leftMargin: 4
                anchors.rightMargin: 4

                function readPrefs()
                {
                    text = alg.settings.value("RMSTREE")
                }

                Component.onCompleted: {
                    readPrefs()
                }
            }
            RendermanButton
            {
                id: rmsPathButton
                text: "pick"
                width: 40
                height: 10
                anchors.right: rmslayout.right
                anchors.rightMargin: 20
                onClicked: {
                    folderPickerDialog.fieldid = rmsPathField
                    folderPickerDialog.setVisible(true)
                }
            }
        }

        RowLayout {
            id: exportlayout
            x:10; y:100
            height: 30
            width: parent.width
            spacing: 6
            Layout.fillWidth: true

            Text {
                id: exportPathLabel
                text: "Export to:"
                horizontalAlignment: Text.AlignRight
                color: "#e6e6e6"
                Layout.minimumWidth: 150
                Layout.maximumWidth: 150
            }
            RendermanTextField {
                id: exportPathField
                placeholderText: "where the asset(s) will be saved"
                anchors.left: exportPathLabel.right
                anchors.right: exportPathButton.left
                anchors.leftMargin: 4
                anchors.rightMargin: 4

                function readPrefs()
                {
                    text = alg.settings.value("saveTo")
                }

                Component.onCompleted: {
                    readPrefs()
                }
            }
            RendermanButton
            {
                id: exportPathButton
                text: "pick"
                width: 40
                height: 10
                anchors.right: exportlayout.right
                anchors.rightMargin: 20
                onClicked: {
                    folderPickerDialog.fieldid = exportPathField
                    folderPickerDialog.setVisible(true)
                }
            }
        }


        RendermanButton
        {
            id: okbutton
            text: "Save"
            onClicked: accept()
            isDefaultButton: true
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 10
            anchors.right: parent.right
            anchors.rightMargin: 10
            width: 100
        }
        RendermanButton
        {
            text: "Cancel"
            onClicked: close()
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 10
            anchors.right: okbutton.left
            anchors.rightMargin: 10
            width: 100
        }

        FileDialog
        {
            id: folderPickerDialog
            visible: false
            title: "Choose the directory ..."
            nameFilters: [ "All files (*)" ]
            selectedNameFilter: "Executable files (*)"
            selectFolder: true
            selectExisting: true
            property var fieldid

            onAccepted:
            {
                fieldid.text = alg.fileIO.urlToLocalFile(fileUrl.toString())
            }

            onVisibleChanged:
            {
                if (visible == false)
                {
                    // alg.log.info("vis OFF")
                    parent.active()
                }
                else
                {
                    // alg.log.info("vis ON")
                }
            }
        }
    }


}