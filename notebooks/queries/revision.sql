-- SQL query to extract data for revision of the event catalog.
SELECT
    Origin.time_value,  -- Event origin time
    POEv.publicID,  -- Event public ID
    Origin.depth_value,  -- Event depth
    Magnitude.magnitude_value,  -- Event magnitude
    Origin.quality_standardError,  -- Standard error of the origin time
    Origin.depth_uncertainty, -- Uncertainty of the event depth
    Origin.latitude_uncertainty,  -- Uncertainty of the event latitude
    Origin.longitude_uncertainty,  -- Uncertainty of the event longitude
    Origin.quality_associatedPhaseCount,  -- Number of associated phases
    Origin.creationInfo_author,  -- Author of the origin creation info
    Event.type,  -- Event type (e.g., earthquake, explosion)
    Origin.creationInfo_agencyID,  -- Agency ID of the origin creation info
    EventDescription.text,  -- Event description text
    Origin.latitude_value,  -- Event latitude
    Origin.longitude_value,  -- Event longitude
    Magnitude.type,  -- Magnitude type (e.g., Mw, ML)
    Origin.methodID,  -- Method ID used for the origin
    Origin.earthModelID  -- Earth model ID used for the origin
FROM Event AS EvMF
    LEFT JOIN PublicObject AS POEv ON EvMF._oid = POEv._oid
    LEFT JOIN PublicObject AS POOri ON EvMF.preferredOriginID=POOri.publicID
    LEFT JOIN Origin ON POOri._oid=Origin._oid
    LEFT JOIN PublicObject AS POMag on EvMF.preferredMagnitudeID=POMag.publicID
    LEFT JOIN Magnitude ON Magnitude._oid = POMag._oid
    LEFT JOIN Event ON Event._oid= POEv._oid
    LEFT JOIN EventDescription ON EvMF._oid = EventDescription._parent_oid
WHERE Origin.time_value BETWEEN