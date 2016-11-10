import QtQuick 2.3
import QtQuick.Controls 1.4
import QtQuick.Controls.Styles 1.4

Button {
  property bool isDefaultButton
  isDefaultButton: false
  property color rmanblue: "#1e94e6"
  property color rmanbluebg: "#303A3F"

  style: ButtonStyle {
    background: Rectangle {
      implicitWidth: 50
      implicitHeight: 24
      border.width: isDefaultButton ? 2 : 1
      border.color: control.pressed ? rmanblue : isDefaultButton ? "#ccc" : "#222"
      radius: 4
      color: control.pressed ? "#323232" : control.hovered ? rmanbluebg : "#292929"
    }
    label: Component {
      Text {
        text: control.text
        font.bold: isDefaultButton
        clip: true
        wrapMode: Text.WordWrap
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignHCenter
        anchors.fill: parent
        color: control.pressed ? "#FFFFFF" : control.hovered ? rmanblue : "#C8C8C8"
      }
    }
  }
}
