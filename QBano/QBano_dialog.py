# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QBanoDialog
                                 A QGIS plugin
 a
                             -------------------
        begin                : 2017-10-14
        git sha              : $Format:%H$
        copyright            : (C) 2017 by CREASIG
        email                : concact@creasig.fr
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



from PyQt5 import *
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import os
import codecs
import unicodedata
import io
import urllib
import simplejson as json

from qgis.core import QgsCoordinateReferenceSystem
from qgis.core import QgsMapLayer
from qgis.core import QgsProject
from qgis.core import QgsRasterFileWriter
from qgis.core import QgsRasterLayer
from qgis.core import QgsMessageLog
from qgis.core import QgsVectorFileWriter
from qgis.core import QgsVectorLayer
from qgis.core import QgsField
from qgis.core import QgsGeometry
from qgis.core import QgsFeature
from qgis.core import *

from xml.dom.minidom import parse, parseString


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'QBano_dialog_base.ui'))


class QBanoDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(QBanoDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

    def chercherCouches(self):
        self._listecouches.clear()
        for name in QgsProject.instance().mapLayers():
            layer = QgsProject.instance().mapLayer(name)

            self._listecouches.addItem(layer.name())


    def remplirChampAdresse(self, valeur):
        self._champadresse.clear()
       
        if valeur != None:
            for name in QgsProject.instance().mapLayers():
                layer = QgsProject.instance().mapLayer(name)

                if layer.name() == valeur:
                    for field in layer.fields():
                        self._champadresse.addItem(field.name())

    def deboguer(self, texte):
        #logging.basicConfig(filename='myapp.log', level=logging.INFO)
        #logging.info(texte)
        pass
      

    def geocoder(self):
        champadresse = self._champadresse.currentText()
        champcouche = self._listecouches.currentText()
        
        for name in QgsProject.instance().mapLayers():
            layer = QgsProject.instance().mapLayer(name)

            if layer.name() == champcouche:
                selected_features = layer.getFeatures()
                
                #Creation de la couche
                vl = QgsVectorLayer("Point?crs=EPSG:4326", "temporary_points", "memory")
                pr = vl.dataProvider()

                # Enter editing mode
                vl.startEditing()
                titre=[];
                for att in layer.fields():
                    titre.append( QgsField((att.name()), QVariant.String))
                titre.append( QgsField("adresse_trouvee", QVariant.String))
                titre.append( QgsField("score", QVariant.String))
                titre.append( QgsField("type", QVariant.String))
                pr.addAttributes(titre);
                vl.commitChanges()
                self._progression.setMinimum(0)
                
                j=0
                for i in selected_features:
                    j=j+1;
                
                self._progression.setMaximum(j)
                
                selected_features = layer.getFeatures()
                j=0
                for i in selected_features:
                    j=j+1;
                    self.deboguer(j)
                    self._progression.setValue(j)
                    QtWidgets.qApp.processEvents()
                    self.deboguer("1")
                    coordonnees={}
                    coordonnees["adresse"] = ''
                    coordonnees["lon"] = 0
                    coordonnees["lat"] = 0
                    coordonnees["score"] = 0
                    coordonnees["type"] = 'empty'
                    if i.attribute(champadresse) is not None and i.attribute(champadresse) and isinstance(i.attribute(champadresse), unicode) :
                        self.deboguer(i.attribute(champadresse))
                        adresse_complete = i.attribute(champadresse)
                        adresse_complete.replace("\""," ")
                        adresse_complete.replace("'"," ")
                        adresse_complete.replace("\\"," ")
                        adresse_complete.replace("."," ")
                        adresse_complete.replace(","," ")
                        adresse_complete.replace(":"," ")
                        adresse_complete.replace(";"," ")
                        self.deboguer(adresse_complete)
                        coordonnees = self.coordonnees(adresse_complete)
                    fet = QgsFeature()
                    if coordonnees != {}:
                        fet.setGeometry( QgsGeometry.fromPointXY(QgsPointXY (coordonnees['lon'],coordonnees['lat']))) 

                    attributs = []
                    numero = 0
                    for att in layer.fields():
                        attributs.append(i.attribute(layer.attributeDisplayName(numero)))
                        numero=numero+1
                    if coordonnees != {}:
                        attributs.append(coordonnees['adresse'])
                        attributs.append(str(coordonnees['score']))
                        attributs.append(str(coordonnees['type']))
                    fet.setAttributes(attributs)
                    pr.addFeatures( [ fet ] )
                    # Commit changes

                vl.commitChanges()
                
                QgsProject.instance().addMapLayer(vl)     

    def coordonnees(self,adresse):

        retour = {}
        try:
            param = {'wt':'json','rows':2,'fl':'score,*'}
            param['q']=unicodedata.normalize('NFD',adresse).encode('ascii','ignore')
            url = urllib.parse.urlencode(param)
            response = urllib.request.urlopen('http://api-adresse.data.gouv.fr/search/?' + url+'&limit=1')
            donnee = io.TextIOWrapper(response)
            # self.deboguer(donnee)
            data = json.load(donnee)
            # self.deboguer(data)
            if len(data['features']) > 0 :
                retour["adresse"] = data['features'][0]['properties']['label']
                retour["lon"] = data['features'][0]['geometry']['coordinates'][0]
                retour["lat"] = data['features'][0]['geometry']['coordinates'][1]
                retour["score"] = data['features'][0]['properties']['score']
                retour["type"] = data['features'][0]['properties']['type']
        except  urllib2.HTTPError as e:
            QMessageBox.critical(self, QtGui.QApplication.translate("QBAN(O)", "QBAN(O)"), QtGui.QApplication.translate("Internetconnexionerror", "Internet connexion error"), QMessageBox.Ok)
            retour = {}
        except  urllib2.URLError as e:
            QMessageBox.critical(self, QtGui.QApplication.translate("QBAN(O)", "QBAN(O)"), QtGui.QApplication.translate("Internetconnexionerror", "Internet connexion error"), QMessageBox.Ok)
            retour = {}
        return retour
