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



import QtQuick 2.2
import Painter 1.0

PainterPlugin
{
	tickIntervalMS: -1 // Disabled, no need for Tick
	jsonServerPort: -1 // Disabled, no need for JSON server

	Component.onCompleted:
	{
	if(alg.version.painter <= "2017.4.2"){
		// create a toolbar button for releases prior to 2018.1.0
		alg.ui.addToolBarWidget("toolbar.qml");
		}

	else{
		// create a plugintoolbar button for releases after 2018.1.0
		alg.ui.addWidgetToPluginToolBar("plugintoolbar.qml");
		}
	}

	onConfigure:
	{
		// open the configuration panel
		rmanPrefsPanel.open()
	}

	RendermanPrefsPanel
	{
		id: rmanPrefsPanel
	}
}
