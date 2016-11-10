import QtQuick 2.3
import QtQuick.Controls 1.4
import QtQuick.Controls.Styles 1.4

TextField {
    style: TextFieldStyle {
        textColor: "#c0c0c0"
        placeholderTextColor: "#333"
        background: Rectangle {
            radius: 2
            implicitWidth: 100
            implicitHeight: 24
            border.color: "#333"
            border.width: 1
            color: "#222"
        }
    }
}