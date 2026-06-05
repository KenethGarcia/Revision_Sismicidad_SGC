-- Query to retrieve data from 'DESTACADO' events at RSNC
SELECT
    Origin.time_value, 
    POEv.publicID, 
    Origin.depth_value, 
    Magnitude.magnitude_value, 
    Origin.quality_standardError, 
    Origin.depth_uncertainty, 
    Origin.latitude_uncertainty, 
    Origin.longitude_uncertainty, 
    Origin.quality_associatedPhaseCount, 
    Origin.creationInfo_author, 
    Event.type, 
    Origin.creationInfo_agencyID, 
    FeltReport.report, 
    Magnitude.type, 
    Origin.methodID, 
    Origin.earthModelID 
FROM Event AS EvMF 
    LEFT JOIN PublicObject AS POEv ON EvMF._oid = POEv._oid 
    LEFT JOIN PublicObject AS POOri ON EvMF.preferredOriginID=POOri.publicID
    LEFT JOIN Origin ON POOri._oid=Origin._oid 
    LEFT JOIN PublicObject AS POMag ON EvMF.preferredMagnitudeID=POMag.publicID
    LEFT JOIN Magnitude ON Magnitude._oid = POMag._oid 
    LEFT JOIN Event ON Event._oid= POEv._oid, FeltReport 
WHERE FeltReport._oid = Event._oid AND Origin.time_value BETWEEN 