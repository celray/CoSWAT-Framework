qgs_template_prj = """<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis projectname="{continent}-{region}" version="3.2.10-Białowieża" saveDateTime="2023-01-23T14:22:31" saveUser="cjames" saveUserFull="Celray James CHAWANDA">
  <homePath path=""/>
  <title>{continent}-{region}</title>
  <autotransaction active="0"/>
  <evaluateDefaultValues active="0"/>
  <trust active="0"/>
  <projectCrs>
    <spatialrefsys>
      <wkt>GEOGCRS["WGS 84",ENSEMBLE["World Geodetic System 1984 ensemble",MEMBER["World Geodetic System 1984 (Transit)"],MEMBER["World Geodetic System 1984 (G730)"],MEMBER["World Geodetic System 1984 (G873)"],MEMBER["World Geodetic System 1984 (G1150)"],MEMBER["World Geodetic System 1984 (G1674)"],MEMBER["World Geodetic System 1984 (G1762)"],MEMBER["World Geodetic System 1984 (G2139)"],ELLIPSOID["WGS 84",6378137,298.257223563,LENGTHUNIT["metre",1]],ENSEMBLEACCURACY[2.0]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],CS[ellipsoidal,2],AXIS["geodetic latitude (Lat)",north,ORDER[1],ANGLEUNIT["degree",0.0174532925199433]],AXIS["geodetic longitude (Lon)",east,ORDER[2],ANGLEUNIT["degree",0.0174532925199433]],USAGE[SCOPE["Horizontal component of 3D system."],AREA["World."],BBOX[-90,-180,90,180]],ID["EPSG",4326]]</wkt>
      <proj4>+proj=longlat +datum=WGS84 +no_defs</proj4>
      <srsid>3452</srsid>
      <srid>4326</srid>
      <authid>EPSG:4326</authid>
      <description>WGS 84</description>
      <projectionacronym>longlat</projectionacronym>
      <ellipsoidacronym>EPSG:7030</ellipsoidacronym>
      <geographicflag>true</geographicflag>
    </spatialrefsys>
  </projectCrs>
  <layer-tree-group>
    <customproperties>
      <Option/>
    </customproperties>
    <layer-tree-group name="Animations" expanded="1" checked="Qt::Checked">
      <customproperties>
        <Option/>
      </customproperties>
    </layer-tree-group>
    <layer-tree-group name="Results" expanded="1" checked="Qt::Checked">
      <customproperties>
        <Option/>
      </customproperties>
    </layer-tree-group>
    <layer-tree-group name="Watershed" expanded="1" checked="Qt::Checked">
      <customproperties>
        <Option/>
      </customproperties>
    </layer-tree-group>
    <layer-tree-group name="Landuse" expanded="1" checked="Qt::Checked">
      <customproperties>
        <Option/>
      </customproperties>
    </layer-tree-group>
    <layer-tree-group name="Soil" expanded="1" checked="Qt::Checked">
      <customproperties>
        <Option/>
      </customproperties>
    </layer-tree-group>
    <layer-tree-group name="Slope" expanded="1" checked="Qt::Checked">
      <customproperties>
        <Option/>
      </customproperties>
    </layer-tree-group>
    <custom-order enabled="0"/>
  </layer-tree-group>
  <snapping-settings minScale="0" enabled="0" tolerance="12" unit="1" mode="2" scaleDependencyMode="0" type="1" self-snapping="0" intersection-snapping="0" maxScale="0">
    <individual-layer-settings/>
  </snapping-settings>
  <relations/>
  <polymorphicRelations/>
  <mapcanvas annotationsVisible="1" name="theMapCanvas">
    <units>degrees</units>
    <extent>
      <xmin>0</xmin>
      <ymin>0</ymin>
      <xmax>0</xmax>
      <ymax>0</ymax>
    </extent>
    <rotation>0</rotation>
    <destinationsrs>
      <spatialrefsys>
        <wkt>GEOGCRS["WGS 84",ENSEMBLE["World Geodetic System 1984 ensemble",MEMBER["World Geodetic System 1984 (Transit)"],MEMBER["World Geodetic System 1984 (G730)"],MEMBER["World Geodetic System 1984 (G873)"],MEMBER["World Geodetic System 1984 (G1150)"],MEMBER["World Geodetic System 1984 (G1674)"],MEMBER["World Geodetic System 1984 (G1762)"],MEMBER["World Geodetic System 1984 (G2139)"],ELLIPSOID["WGS 84",6378137,298.257223563,LENGTHUNIT["metre",1]],ENSEMBLEACCURACY[2.0]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],CS[ellipsoidal,2],AXIS["geodetic latitude (Lat)",north,ORDER[1],ANGLEUNIT["degree",0.0174532925199433]],AXIS["geodetic longitude (Lon)",east,ORDER[2],ANGLEUNIT["degree",0.0174532925199433]],USAGE[SCOPE["Horizontal component of 3D system."],AREA["World."],BBOX[-90,-180,90,180]],ID["EPSG",4326]]</wkt>
        <proj4>+proj=longlat +datum=WGS84 +no_defs</proj4>
        <srsid>3452</srsid>
        <srid>4326</srid>
        <authid>EPSG:4326</authid>
        <description>WGS 84</description>
        <projectionacronym>longlat</projectionacronym>
        <ellipsoidacronym>EPSG:7030</ellipsoidacronym>
        <geographicflag>true</geographicflag>
      </spatialrefsys>
    </destinationsrs>
    <rendermaptile>0</rendermaptile>
    <expressionContextScope/>
  </mapcanvas>
  <projectModels/>
  <legend updateDrawingOrder="true">
    <legendgroup name="Animations" checked="Qt::Checked" open="true"/>
    <legendgroup name="Results" checked="Qt::Checked" open="true"/>
    <legendgroup name="Watershed" checked="Qt::Checked" open="true"/>
    <legendgroup name="Landuse" checked="Qt::Checked" open="true"/>
    <legendgroup name="Soil" checked="Qt::Checked" open="true"/>
    <legendgroup name="Slope" checked="Qt::Checked" open="true"/>
  </legend>
  <mapViewDocks/>
  <mapViewDocks3D/>
  <main-annotation-layer refreshOnNotifyMessage="" autoRefreshEnabled="0" autoRefreshTime="0" refreshOnNotifyEnabled="0" type="annotation" legendPlaceholderImage="">
    <id>Annotations_83914ae2_ff7f_4aaf_ab05_44010dbbf7bb</id>
    <datasource></datasource>
    <keywordList>
      <value></value>
    </keywordList>
    <layername>Annotations</layername>
    <srs>
      <spatialrefsys>
        <wkt>GEOGCRS["WGS 84",ENSEMBLE["World Geodetic System 1984 ensemble",MEMBER["World Geodetic System 1984 (Transit)"],MEMBER["World Geodetic System 1984 (G730)"],MEMBER["World Geodetic System 1984 (G873)"],MEMBER["World Geodetic System 1984 (G1150)"],MEMBER["World Geodetic System 1984 (G1674)"],MEMBER["World Geodetic System 1984 (G1762)"],MEMBER["World Geodetic System 1984 (G2139)"],ELLIPSOID["WGS 84",6378137,298.257223563,LENGTHUNIT["metre",1]],ENSEMBLEACCURACY[2.0]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],CS[ellipsoidal,2],AXIS["geodetic latitude (Lat)",north,ORDER[1],ANGLEUNIT["degree",0.0174532925199433]],AXIS["geodetic longitude (Lon)",east,ORDER[2],ANGLEUNIT["degree",0.0174532925199433]],USAGE[SCOPE["Horizontal component of 3D system."],AREA["World."],BBOX[-90,-180,90,180]],ID["EPSG",4326]]</wkt>
        <proj4>+proj=longlat +datum=WGS84 +no_defs</proj4>
        <srsid>3452</srsid>
        <srid>4326</srid>
        <authid>EPSG:4326</authid>
        <description>WGS 84</description>
        <projectionacronym>longlat</projectionacronym>
        <ellipsoidacronym>EPSG:7030</ellipsoidacronym>
        <geographicflag>true</geographicflag>
      </spatialrefsys>
    </srs>
    <resourceMetadata>
      <identifier></identifier>
      <parentidentifier></parentidentifier>
      <language></language>
      <type></type>
      <title></title>
      <abstract></abstract>
      <links/>
      <fees></fees>
      <encoding></encoding>
      <crs>
        <spatialrefsys>
          <wkt></wkt>
          <proj4></proj4>
          <srsid>0</srsid>
          <srid>0</srid>
          <authid></authid>
          <description></description>
          <projectionacronym></projectionacronym>
          <ellipsoidacronym></ellipsoidacronym>
          <geographicflag>false</geographicflag>
        </spatialrefsys>
      </crs>
      <extent/>
    </resourceMetadata>
    <items/>
    <layerOpacity>1</layerOpacity>
    <blendMode>0</blendMode>
    <paintEffect/>
  </main-annotation-layer>
  <projectlayers/>
  <layerorder/>
  <properties>
    <Digitizing>
      <AvoidIntersectionsMode type="int">0</AvoidIntersectionsMode>
    </Digitizing>
    <Gui>
      <CanvasColorBluePart type="int">255</CanvasColorBluePart>
      <CanvasColorGreenPart type="int">255</CanvasColorGreenPart>
      <CanvasColorRedPart type="int">255</CanvasColorRedPart>
      <SelectionColorAlphaPart type="int">255</SelectionColorAlphaPart>
      <SelectionColorBluePart type="int">0</SelectionColorBluePart>
      <SelectionColorGreenPart type="int">255</SelectionColorGreenPart>
      <SelectionColorRedPart type="int">255</SelectionColorRedPart>
    </Gui>
    <Legend>
      <filterByMap type="bool">false</filterByMap>
    </Legend>
    <Measure>
      <Ellipsoid type="QString">EPSG:7030</Ellipsoid>
    </Measure>
    <Measurement>
      <AreaUnits type="QString"></AreaUnits>
      <DistanceUnits type="QString"></DistanceUnits>
    </Measurement>
    <PAL>
      <CandidatesLinePerCM type="double">5</CandidatesLinePerCM>
      <CandidatesPolygonPerCM type="double">2.5</CandidatesPolygonPerCM>
      <DrawRectOnly type="bool">false</DrawRectOnly>
      <DrawUnplaced type="bool">false</DrawUnplaced>
      <PlacementEngineVersion type="int">1</PlacementEngineVersion>
      <SearchMethod type="int">0</SearchMethod>
      <ShowingAllLabels type="bool">false</ShowingAllLabels>
      <ShowingCandidates type="bool">false</ShowingCandidates>
      <ShowingPartialsLabels type="bool">true</ShowingPartialsLabels>
      <TextFormat type="int">0</TextFormat>
      <UnplacedColor type="QString">255,0,0,255</UnplacedColor>
    </PAL>
    <Paths>
      <Absolute type="bool">false</Absolute>
    </Paths>
    <PositionPrecision>
      <Automatic type="bool">true</Automatic>
      <DecimalPlaces type="int">2</DecimalPlaces>
    </PositionPrecision>
    <SpatialRefSys>
      <ProjectionsEnabled type="int">1</ProjectionsEnabled>
    </SpatialRefSys>
    <{continent}-{region}>
      <delin>
        <isHUC type="bool">false</isHUC>
      </delin>
      <params>
        <burninDepth type="int">100</burninDepth>
        <channelDepthExponent type="double">0.4</channelDepthExponent>
        <channelDepthMultiplier type="double">0.13</channelDepthMultiplier>
        <channelWidthExponent type="double">0.6</channelWidthExponent>
        <channelWidthMultiplier type="double">1.29</channelWidthMultiplier>
        <mainLengthMultiplier type="double">1</mainLengthMultiplier>
        <meanSlopeMultiplier type="double">1</meanSlopeMultiplier>
        <reachSlopeMultiplier type="double">1</reachSlopeMultiplier>
        <tributaryLengthMultiplier type="double">1</tributaryLengthMultiplier>
        <tributarySlopeMultiplier type="double">1</tributarySlopeMultiplier>
        <upslopeHRUDrain type="int">90</upslopeHRUDrain>
      </params>
    </{continent}-{region}>
  </properties>
  <dataDefinedServerProperties>
    <Option type="Map">
      <Option name="name" value="" type="QString"/>
      <Option name="properties"/>
      <Option name="type" value="collection" type="QString"/>
    </Option>
  </dataDefinedServerProperties>
  <visibility-presets/>
  <transformContext/>
  <projectMetadata>
    <identifier></identifier>
    <parentidentifier></parentidentifier>
    <language></language>
    <type></type>
    <title>{continent}-{region}</title>
    <abstract></abstract>
    <links/>
    <author>Celray James CHAWANDA</author>
    <creation>2023-01-23T14:21:41</creation>
  </projectMetadata>
  <Annotations/>
  <Layouts/>
  <Bookmarks/>
  <ProjectViewSettings UseProjectScales="0">
    <Scales/>
  </ProjectViewSettings>
  <ProjectTimeSettings cumulativeTemporalRange="0" timeStepUnit="h" timeStep="1" frameRate="1"/>
  <ProjectDisplaySettings>
    <BearingFormat id="bearing">
      <Option type="Map">
        <Option name="decimal_separator" value="" type="QChar"/>
        <Option name="decimals" value="6" type="int"/>
        <Option name="direction_format" value="0" type="int"/>
        <Option name="rounding_type" value="0" type="int"/>
        <Option name="show_plus" value="false" type="bool"/>
        <Option name="show_thousand_separator" value="true" type="bool"/>
        <Option name="show_trailing_zeros" value="false" type="bool"/>
        <Option name="thousand_separator" value="" type="QChar"/>
      </Option>
    </BearingFormat>
  </ProjectDisplaySettings>
</qgis>
"""