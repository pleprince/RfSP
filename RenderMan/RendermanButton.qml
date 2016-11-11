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
      color: control.pressed ? "#323232" : control.hovered ? rmanbluebg : "#333"
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
