template_string = '''<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis projectname="{project_name}" saveUser="cjames" version="3.22.10-Białowieża" saveUserFull="Celray James CHAWANDA">
  <homePath path=""/>
  <title>{project_name}</title>
  <projectlayers>
    <maplayer legendPlaceholderImage="" autoRefreshTime="0" wkbType="MultiLineString" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" maxScale="0" geometry="Line" autoRefreshEnabled="0" symbologyReferenceScale="-1" styleCategories="AllStyleCategories" simplifyLocal="1" readOnly="0" hasScaleBasedVisibilityFlag="0" simplifyAlgorithm="0" simplifyMaxScale="1" simplifyDrawingTol="1" simplifyDrawingHints="0" type="vector" labelsEnabled="0" minScale="100000000">
      <id>Channel_reaches__rivs1__{rivs_1_id}</id>
      <datasource>./Watershed/Shapes/rivs1.shp</datasource>
    </maplayer>
    <maplayer legendPlaceholderImage="" autoRefreshTime="0" wkbType="MultiLineString" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" maxScale="0" geometry="Line" autoRefreshEnabled="0" symbologyReferenceScale="-1" styleCategories="AllStyleCategories" simplifyLocal="1" readOnly="0" hasScaleBasedVisibilityFlag="0" simplifyAlgorithm="0" simplifyMaxScale="1" simplifyDrawingTol="1" simplifyDrawingHints="1" type="vector" labelsEnabled="1" minScale="100000000">
      <id>Channels__{dem_file_name_underscore_hyphens}channel__{channel_shape_id}</id>
      <datasource>./Watershed/Shapes/{dem_file_name}channel.shp</datasource>
    </maplayer>
    <maplayer hasScaleBasedVisibilityFlag="0" legendPlaceholderImage="" autoRefreshTime="0" styleCategories="AllStyleCategories" autoRefreshEnabled="0" refreshOnNotifyMessage="" refreshOnNotifyEnabled="0" type="raster" minScale="1e+08" maxScale="0">
      <id>DEM__{dem_file_name_underscore_hyphens}__{dem_id}</id>
      <datasource>./Watershed/Rasters/DEM/{dem_file_name}.tif</datasource>
      <keywordList>
        <value></value>
      </keywordList>
      <layername>DEM ({dem_file_name})</layername>
      <srs>
        <spatialrefsys>
          <authid>{authid}</authid>
        </spatialrefsys>
      </srs>
    </maplayer>
    <maplayer legendPlaceholderImage="" autoRefreshTime="0" wkbType="MultiPolygon" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" maxScale="0" geometry="Polygon" autoRefreshEnabled="0" symbologyReferenceScale="-1" styleCategories="AllStyleCategories" simplifyLocal="1" readOnly="0" hasScaleBasedVisibilityFlag="0" simplifyAlgorithm="0" simplifyMaxScale="1" simplifyDrawingTol="1" simplifyDrawingHints="1" type="vector" labelsEnabled="1" minScale="100000000">
      <id>Full_LSUs__lsus1__{lsus_shape_id}</id>
      <datasource>./Watershed/Shapes/lsus1.shp</datasource>
    </maplayer>
    <maplayer hasScaleBasedVisibilityFlag="0" legendPlaceholderImage="" autoRefreshTime="0" styleCategories="AllStyleCategories" autoRefreshEnabled="0" refreshOnNotifyMessage="" refreshOnNotifyEnabled="0" type="raster" minScale="1e+08" maxScale="0">
      <id>Hillshade__{dem_file_name_underscore_hyphens}hillshade__{hillshade_id}</id>
      <datasource>./Watershed/Rasters/DEM/{dem_file_name}hillshade.tif</datasource>
    </maplayer>
    <maplayer legendPlaceholderImage="" autoRefreshTime="0" wkbType="Point" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" maxScale="-4.6566099999999998e-10" geometry="Point" autoRefreshEnabled="0" symbologyReferenceScale="-1" styleCategories="AllStyleCategories" simplifyLocal="1" readOnly="0" hasScaleBasedVisibilityFlag="0" simplifyAlgorithm="0" simplifyMaxScale="1" simplifyDrawingTol="1" simplifyDrawingHints="0" type="vector" labelsEnabled="0" minScale="100000000">
      <id>Inlets_outlets__outlets__{outlets_id}</id>
      <datasource>./Watershed/Shapes/outlets.shp</datasource>
    </maplayer>
    <maplayer hasScaleBasedVisibilityFlag="0" legendPlaceholderImage="" autoRefreshTime="0" styleCategories="AllStyleCategories" autoRefreshEnabled="0" refreshOnNotifyMessage="" refreshOnNotifyEnabled="0" type="raster" minScale="1e+08" maxScale="0">
      <id>Landuses__{land_use_file_name_underscore_hyphens}__{landuse_id}</id>
      <datasource>./Watershed/Rasters/Landuse/{land_use_file_name}.tif</datasource>
      <keywordList>
        <value></value>
      </keywordList>
      <layername>Landuses ({land_use_file_name})</layername>
      <srs>
        <spatialrefsys>
          <authid>{authid}</authid>
        </spatialrefsys>
      </srs>
    </maplayer>
    <maplayer legendPlaceholderImage="" autoRefreshTime="0" wkbType="MultiLineString" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" maxScale="0" geometry="Line" autoRefreshEnabled="0" symbologyReferenceScale="-1" styleCategories="AllStyleCategories" simplifyLocal="1" readOnly="0" hasScaleBasedVisibilityFlag="0" simplifyAlgorithm="0" simplifyMaxScale="1" simplifyDrawingTol="1" simplifyDrawingHints="0" type="vector" labelsEnabled="1" minScale="100000000">
      <id>Lakes__{lakes_file_name_underscore_hyphens}stream__{lakes_id}</id>
      <datasource>./Watershed/Shapes/{lakes_file_name}.shp</datasource>
    </maplayer>
    <maplayer legendPlaceholderImage="" autoRefreshTime="0" wkbType="Point" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" maxScale="-4.6566099999999998e-10" geometry="Point" autoRefreshEnabled="0" symbologyReferenceScale="-1" styleCategories="AllStyleCategories" simplifyLocal="1" readOnly="0" hasScaleBasedVisibilityFlag="0" simplifyAlgorithm="0" simplifyMaxScale="1" simplifyDrawingTol="1" simplifyDrawingHints="0" type="vector" labelsEnabled="0" minScale="100000000">
      <id>Pt_sources_and_reservoirs__reservoirs__{reservoir_shape_id}</id>
      <datasource>./Watershed/Shapes/reservoirs.shp</datasource>
    </maplayer>
    <maplayer legendPlaceholderImage="" autoRefreshTime="0" wkbType="Point" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" maxScale="-4.6566099999999998e-10" geometry="Point" autoRefreshEnabled="0" symbologyReferenceScale="-1" styleCategories="AllStyleCategories" simplifyLocal="1" readOnly="0" hasScaleBasedVisibilityFlag="0" simplifyAlgorithm="0" simplifyMaxScale="1" simplifyDrawingTol="1" simplifyDrawingHints="0" type="vector" labelsEnabled="0" minScale="100000000">
      <id>Selected_inlets_outlets__outlets_sel__{se_outlets_shape_id}</id>
      <datasource>./Watershed/Shapes/outlets_sel.shp</datasource>
    </maplayer>
    <maplayer hasScaleBasedVisibilityFlag="0" legendPlaceholderImage="" autoRefreshTime="0" styleCategories="AllStyleCategories" autoRefreshEnabled="0" refreshOnNotifyMessage="" refreshOnNotifyEnabled="0" type="raster" minScale="1e+08" maxScale="0">
      <id>Soils__{soils_file_name_underscore_hyphens}__{soils_id}</id>
      <datasource>./Watershed/Rasters/Soil/{soils_file_name}.tif</datasource>
      <keywordList>
        <value></value>
      </keywordList>
      <layername>Soils ({soils_file_name})</layername>
      <srs>
        <spatialrefsys>
          <authid>{authid}</authid>
        </spatialrefsys>
      </srs>
    </maplayer>
    <maplayer legendPlaceholderImage="" autoRefreshTime="0" wkbType="MultiLineString" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" maxScale="0" geometry="Line" autoRefreshEnabled="0" symbologyReferenceScale="-1" styleCategories="AllStyleCategories" simplifyLocal="1" readOnly="0" hasScaleBasedVisibilityFlag="0" simplifyAlgorithm="0" simplifyMaxScale="1" simplifyDrawingTol="1" simplifyDrawingHints="1" type="vector" labelsEnabled="0" minScale="100000000">
      <id>Stream_burn_in__{burn_file_name_underscore_hyphens}__{burn_shape_id}</id>
      <datasource>./Watershed/Shapes/{burn_file_name}.shp</datasource>
    </maplayer>
    <maplayer legendPlaceholderImage="" autoRefreshTime="0" wkbType="MultiLineString" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" maxScale="0" geometry="Line" autoRefreshEnabled="0" symbologyReferenceScale="-1" styleCategories="AllStyleCategories" simplifyLocal="1" readOnly="0" hasScaleBasedVisibilityFlag="0" simplifyAlgorithm="0" simplifyMaxScale="1" simplifyDrawingTol="1" simplifyDrawingHints="0" type="vector" labelsEnabled="1" minScale="100000000">
      <id>Streams__{dem_file_name_underscore_hyphens}stream__{stream_shape_id}</id>
      <datasource>./Watershed/Shapes/{dem_file_name}stream.shp</datasource>
    </maplayer>
    <maplayer legendPlaceholderImage="" autoRefreshTime="0" wkbType="MultiPolygon" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" maxScale="-4.6566099999999998e-10" geometry="Polygon" autoRefreshEnabled="0" symbologyReferenceScale="-1" styleCategories="AllStyleCategories" simplifyLocal="1" readOnly="0" hasScaleBasedVisibilityFlag="0" simplifyAlgorithm="0" simplifyMaxScale="1" simplifyDrawingTol="1" simplifyDrawingHints="1" type="vector" labelsEnabled="1" minScale="100000000">
      <id>Subbasins__subs1__{subbasins_id}</id>
      <datasource>./Watershed/Shapes/subs1.shp</datasource>
    </maplayer>
  </projectlayers>
  
  <properties>
    <{project_name}>
      <delin>
        <DEM type="QString">./Watershed/Rasters/DEM/{dem_file_name}.tif</DEM>
        <burn type="QString">./Watershed/Shapes/{burn_file_name}.shp</burn>
        <channels type="QString">./Watershed/Shapes/{dem_file_name}channel.shp</channels>
        <delinNet type="QString">./Watershed/Shapes/{dem_file_name}stream.shp</delinNet>
        <drainageTable type="QString"></drainageTable>
        <existingWshed type="int">0</existingWshed>
        <extraOutlets type="QString"></extraOutlets>
        <gridDrainage type="int">0</gridDrainage>
        <gridSize type="int">0</gridSize>
        <isHUC type="bool">false</isHUC>
        <lakePointsAdded type="int">0</lakePointsAdded>
        <lakes type="QString">./Watershed/Shapes/{lakes_file_name}.shp</lakes>
        <lakesDone type="int">0</lakesDone>
        <net type="QString">./Watershed/Shapes/{dem_file_name}stream.shp</net>
        <outlets type="QString">./Watershed/Shapes/outlets_sel.shp</outlets>
        <snapOutlets type="QString">./Watershed/Shapes/outlets_sel_snap.shp</snapOutlets>
        <snapThreshold type="int">300</snapThreshold>
        <streamDrainage type="int">1</streamDrainage>
        <subbasins type="QString">./Watershed/Shapes/{dem_file_name}subbasins.shp</subbasins>
        <subsNoLakes type="QString">./Watershed/Shapes/subsNoLakes.shp</subsNoLakes>
        <thresholdCh type="int">{thresholdCh}</thresholdCh>
        <thresholdSt type="int">{thresholdSt}</thresholdSt>
        <useGridModel type="int">0</useGridModel>
        <useOutlets type="int">1</useOutlets>
        <verticalUnits type="QString">metres</verticalUnits>
        <wshed type="QString">./Watershed/Shapes/{dem_file_name}wshed.shp</wshed>
      </delin>
      <hru>
        <areaVal type="int">0</areaVal>
        <elevBandsThreshold type="int">0</elevBandsThreshold>
        <isArea type="int">1</isArea>
        <isDominantHRU type="int">0</isDominantHRU>
        <isMultiple type="int">1</isMultiple>
        <isTarget type="int">0</isTarget>
        <landuseVal type="int">0</landuseVal>
        <numElevBands type="int">0</numElevBands>
        <slopeBands type="QString">[0, 9999]</slopeBands>
        <slopeBandsFile type="QString"></slopeBandsFile>
        <slopeVal type="int">0</slopeVal>
        <soilVal type="int">0</soilVal>
        <targetVal type="int">0</targetVal>
        <useArea type="int">0</useArea>
      </hru>
      <landuse>
        <file type="QString">./Watershed/Rasters/Landuse/{land_use_file_name}.tif</file>
        <plant type="QString">plant</plant>
        <table type="QString">landuse_lookup</table>
        <urban type="QString">urban</urban>
        <water type="int">210</water>
      </landuse>
      <lsu>
        <channelMergeByPercent type="int">1</channelMergeByPercent>
        <channelMergeVal type="int">0</channelMergeVal>
        <floodplainFile type="QString"></floodplainFile>
        <thresholdResNoFlood type="int">101</thresholdResNoFlood>
        <useLandscapes type="int">0</useLandscapes>
        <useLeftRight type="int">0</useLeftRight>
      </lsu>
      <params>
        <burninDepth type="int">{burnInDepth}</burninDepth>
        <channelDepthExponent type="double">0.4</channelDepthExponent>
        <channelDepthMultiplier type="double">0.13</channelDepthMultiplier>
        <channelWidthExponent type="double">0.6</channelWidthExponent>
        <channelWidthMultiplier type="double">1.0</channelWidthMultiplier>
        <mainLengthMultiplier type="double">1</mainLengthMultiplier>
        <meanSlopeMultiplier type="double">1</meanSlopeMultiplier>
        <reachSlopeMultiplier type="double">1</reachSlopeMultiplier>
        <tributaryLengthMultiplier type="double">1</tributaryLengthMultiplier>
        <tributarySlopeMultiplier type="double">1</tributarySlopeMultiplier>
        <upslopeHRUDrain type="int">90</upslopeHRUDrain>
      </params>
      <soil>
        <database type="QString">./{project_name}.sqlite</database>
        <databaseTable type="QString">usersoil</databaseTable>
        <file type="QString">./Watershed/Rasters/Soil/{soils_file_name}.tif</file>
        <table type="QString">soil_lookup</table>
        <useSSURGO type="int">0</useSSURGO>
        <useSTATSGO type="int">0</useSTATSGO>
      </soil>
    </{project_name}>
  </properties>
</qgis>
'''