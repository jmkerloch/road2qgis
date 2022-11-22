# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Road2QGISDialog
                                 A QGIS plugin
 Plugin faisant appel au calcul d'itinéraires du Géoportail pour intégration dans QGIS
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2022-11-07
        git sha              : $Format:%H$
        copyright            : (C) 2022 by azarz
        email                : amaury.zarzelli@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from functools import partial
import json
import time

from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRectangle, QgsPoint, QgsPointXY,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsJsonUtils
)

from road2qgis.ui.location_selector import LocationSelector
from road2qgis.core.road2_request import Road2Request

class Road2QGISDialog(QtWidgets.QDialog):
    def __init__(self, iface):
        """Constructor."""
        self.iface = iface
        QtWidgets.QDialog.__init__(self)
        self.setWindowTitle("Calcul d'itinéraires du Géoportail")

        self.layout = QtWidgets.QVBoxLayout()
        self.central_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(self.central_layout)

        self.locations_layout = QtWidgets.QVBoxLayout()
        self.central_layout.addLayout(self.locations_layout)
        location_label = QtWidgets.QLabel()
        location_label.setText("Points de l'itinéraire")
        self.locations_layout.addWidget(location_label)

        self._intermediate_locationselectors = []
        self.location_layouts = []
        self.remove_intermediate_buttons = []
        self._add_location_selectors()
        self._add_remove_intermediate_buttons()

        self._current_intermediates = 0

        self.add_intermediate_button = QtWidgets.QPushButton()
        self.add_intermediate_button.setFixedSize(28, 28)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/plugins/road2qgis/res/plus.png"))
        self.add_intermediate_button.setIcon(icon)
        self.location_layout_end.addWidget(self.add_intermediate_button)
        self.add_intermediate_button.clicked.connect(lambda: self._display_intermediate_location_selector())

        self.parameters_layout = QtWidgets.QGridLayout()
        self.parameters_layout.setSpacing(5)

        self.central_layout.addItem(QtWidgets.QSpacerItem(20, 20))
        self.central_layout.addLayout(self.parameters_layout)

        parameter_label = QtWidgets.QLabel()
        parameter_label.setText("Paramètres de l'itinéraire")
        parameter_label.setFixedHeight(30)
        self.parameters_layout.addWidget(parameter_label, 0, 0)

        profil_label = QtWidgets.QLabel()
        profil_label.setText("Profil :")
        self.parameters_layout.addWidget(profil_label, 1, 0)
        self.profile_combo = QtWidgets.QComboBox()
        self.profile_combo.addItems(["car", "pedestrian"])
        self.parameters_layout.addWidget(self.profile_combo, 1, 1)

        opti_label = QtWidgets.QLabel()
        opti_label.setText("Optimisation :")
        self.parameters_layout.addWidget(opti_label, 1, 2)
        self.opti_combo = QtWidgets.QComboBox()
        self.opti_combo.addItems(["fastest", "shortest"])
        self.parameters_layout.addWidget(self.opti_combo, 1, 3)

        timeunit_label = QtWidgets.QLabel()
        timeunit_label.setText("Unité de temps :")
        self.parameters_layout.addWidget(timeunit_label, 2, 0)
        self.timeunit_combo = QtWidgets.QComboBox()
        self.timeunit_combo.addItems(["second", "minute", "hour"])
        self.parameters_layout.addWidget(self.timeunit_combo, 2, 1)

        distunit_label = QtWidgets.QLabel()
        distunit_label.setText("Unité de distance :")
        self.parameters_layout.addWidget(distunit_label, 2, 2)
        self.distunit_combo = QtWidgets.QComboBox()
        self.distunit_combo.addItems(["meter", "kilometer"])
        self.parameters_layout.addWidget(self.distunit_combo, 2, 3)

        global_check_label = QtWidgets.QLabel()
        global_check_label.setText("Afficher l'itinéraire global")
        self.parameters_layout.addWidget(global_check_label, 3, 0)
        self.global_check = QtWidgets.QCheckBox()
        self.global_check.setChecked(True)
        self.global_check.clicked.connect(self._check_send_button_enabled)
        self.parameters_layout.addWidget(self.global_check, 3, 1)

        step_by_step_check_label = QtWidgets.QLabel()
        step_by_step_check_label.setText("Afficher les étapes")
        self.parameters_layout.addWidget(step_by_step_check_label, 3, 2)
        self.step_by_step_check = QtWidgets.QCheckBox()
        self.step_by_step_check.clicked.connect(self._check_send_button_enabled)
        self.parameters_layout.addWidget(self.step_by_step_check, 3, 3)

        self.send_route_button = QtWidgets.QPushButton(self)
        self.send_route_button.setText("Calculer l'itinéraire")
        self.send_route_button.setMaximumWidth(200)
        self.send_route_button.clicked.connect(self.compute_route)
        self.send_route_button.setEnabled(False)
        self.layout.addWidget(self.send_route_button)

        self.setLayout(self.layout)
        self.setFixedSize(self.sizeHint())

    def compute_route(self):
        """
        """
        url = "https://wxs.ign.fr/calcul/geoportail/itineraire/rest/1.0.0/route"
        start = self.location_selector_start.longitude, self.location_selector_start.latitude
        end = self.location_selector_end.longitude, self.location_selector_end.latitude

        intermediates = []
        for location_selector in self._intermediate_locationselectors:
            if location_selector.latitude is not None:
                intermediates.append((location_selector.longitude, location_selector.latitude))

        options = {
            "intermediates": intermediates,
            "profile": self.profile_combo.currentText(),
            "optimization": self.opti_combo.currentText(),
            "timeUnit": self.timeunit_combo.currentText(),
            "distanceUnit": self.distunit_combo.currentText(),
            "getSteps": self.step_by_step_check.isChecked(),
        }

        req = Road2Request(url, "bdtopo-osrm", start, end, **options)
        resp = req.doRequest()
        self._add_route_to_canvas(resp)

    def _add_route_to_canvas(self, road2_response):
        """
        """
        timestamp = time.time()
        if self.step_by_step_check.isChecked():
            portions_features = road2_response.getFeatureCollections()
            for i in range(len(portions_features)):
                feature_string = json.dumps(portions_features[i])
                codec = QtCore.QTextCodec.codecForName("UTF-8")
                fields = QgsJsonUtils.stringToFields(feature_string, codec)
                feats = QgsJsonUtils.stringToFeatureList(feature_string, fields, codec)

                layer = QgsVectorLayer(
                    "LineString",
                    "itineraire_etapes_portion_{}".format(i + 1),
                    "memory"
                )
                provider = layer.dataProvider()
                provider.addAttributes(fields)
                layer.updateFields()
                provider.addFeatures(feats)
                layer.updateExtents()

                QgsProject.instance().addMapLayer(layer)
                layer.renderer().symbol().setWidth(1.5)
                layer.triggerRepaint()


        if self.global_check.isChecked():
            feature_string = json.dumps(road2_response.getFeature())
            codec = QtCore.QTextCodec.codecForName("UTF-8")
            fields = QgsJsonUtils.stringToFields(feature_string, codec)
            feats = QgsJsonUtils.stringToFeatureList(feature_string, fields, codec)

            layer = QgsVectorLayer("LineString", "itineraire", "memory")
            provider = layer.dataProvider()
            provider.addAttributes(fields)
            layer.updateFields()
            provider.addFeatures(feats)
            layer.updateExtents()

            QgsProject.instance().addMapLayer(layer)
            layer.renderer().symbol().setWidth(1.5)
            layer.triggerRepaint()

        route_crs = QgsCoordinateReferenceSystem.fromEpsgId(4326)
        project_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        tr = QgsCoordinateTransform(route_crs, project_crs, QgsProject.instance())

        point_min = QgsPoint(road2_response.bbox[0], road2_response.bbox[1])
        point_max = QgsPoint(road2_response.bbox[2], road2_response.bbox[3])
        point_min.transform(tr)
        point_max.transform(tr)
        canvas = self.iface.mapCanvas()
        canvas.setExtent(QgsRectangle(QgsPointXY(point_min), QgsPointXY(point_max)))

    def _display_intermediate_location_selector(self):
        """
        """
        for index in range(len(self._intermediate_locationselectors)):
            if not self._intermediate_locationselectors[index].isVisible():
                break
        self._intermediate_locationselectors[index].setHidden(False)
        self.remove_intermediate_buttons[index].setHidden(False)
        self._current_intermediates += 1
        if (self._current_intermediates == 9):
            self.add_intermediate_button.setHidden(True)
        self.setFixedSize(self.sizeHint())

    def _hide_intermediate_location_selector(self, index):
        """
        """
        if (self._current_intermediates == 10):
            self.add_intermediate_button.setHidden(False)
        self._intermediate_locationselectors[index].setHidden(True)
        self._intermediate_locationselectors[index].text = ""
        self._intermediate_locationselectors[index].textbox.setText("")
        self._intermediate_locationselectors[index].latitude = None
        self._intermediate_locationselectors[index].longitude = None
        self.remove_intermediate_buttons[index].setHidden(True)
        self._current_intermediates -= 1

        self.setFixedSize(self.sizeHint())

    def _add_location_selectors(self):
        """
        """
        # Start
        self.location_layout_start = QtWidgets.QHBoxLayout()
        self.locations_layout.addLayout(self.location_layout_start)
        self.location_layout_start.setAlignment(QtCore.Qt.AlignLeft)
        self.location_selector_start = LocationSelector("Départ", self.iface)
        self.location_layout_start.addWidget(self.location_selector_start)
        self.location_selector_start.location_selected_signal.connect(self._check_send_button_enabled)
        # Intermediates
        for _ in range(10):
            location_layout_inter = QtWidgets.QHBoxLayout()
            self.locations_layout.addLayout(location_layout_inter)
            self.location_layouts.append(location_layout_inter)
            location_selector_inter = LocationSelector("Étape", self.iface)
            self._intermediate_locationselectors.append(location_selector_inter)
            location_layout_inter.addWidget(location_selector_inter)
            location_selector_inter.setHidden(True)
        # End
        self.location_layout_end = QtWidgets.QHBoxLayout()
        self.locations_layout.addLayout(self.location_layout_end)
        self.location_selector_end = LocationSelector("Arrivée", self.iface)
        self.location_layout_end.addWidget(self.location_selector_end)
        self.location_layout_end.setAlignment(QtCore.Qt.AlignLeft)
        self.location_selector_end.location_selected_signal.connect(self._check_send_button_enabled)

    def _add_remove_intermediate_buttons(self):
        """
        """
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/plugins/road2qgis/res/x.png"))

        for i in range(10):
            remove_intermediate_button = QtWidgets.QPushButton()
            remove_intermediate_button.setFixedSize(28, 28)
            remove_intermediate_button.setIcon(icon)
            remove_intermediate_button.clicked.connect(partial(self._hide_intermediate_location_selector, i))
            self.remove_intermediate_buttons.append(remove_intermediate_button)
            self.location_layouts[i].addWidget(remove_intermediate_button)
            remove_intermediate_button.setHidden(True)

    def _check_send_button_enabled(self):
        """
        """
        if self.global_check.isChecked() or self.step_by_step_check.isChecked() :
            if self.location_selector_start.latitude is not None and self.location_selector_end.latitude is not None:
                self.send_route_button.setEnabled(True)
            else :
                self.send_route_button.setEnabled(False)
        else :
            self.send_route_button.setEnabled(False)
