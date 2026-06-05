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
    Comment.text,
    Magnitude.type,
    Origin.methodID,
    Origin.earthModelID
FROM Event AS EvMF
    left join PublicObject AS POEv ON EvMF._oid = POEv._oid
    left join PublicObject AS POOri ON EvMF.preferredOriginID=POOri.publicID
    left join Origin ON POOri._oid=Origin._oid
    left join PublicObject AS POMag ON EvMF.preferredMagnitudeID=POMag.publicID
    left join Magnitude ON Magnitude._oid = POMag._oid
    left join Event ON Event._oid= POEv._oid, Comment
WHERE Comment._parent_oid = Event._oid AND Comment.text LIKE '%DESTACADO%' AND Origin.time_value BETWEEN
