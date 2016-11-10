import QtQuick 2.2
import Painter 1.0

PainterPlugin
{
	tickIntervalMS: -1 // Disabled, no need for Tick
	jsonServerPort: -1 // Disabled, no need for JSON server

	Component.onCompleted:
	{
		// create a toolbar button
		alg.ui.addToolBarWidget("toolbar.qml");
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