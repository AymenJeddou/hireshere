"""One module per hiring system. Each exposes parse(data, board) and async fetch(client, board)."""

from pipeline.connectors import (
    ashby,
    greenhouse,
    lever,
    recruitee,
    remoteok,
    smartrecruiters,
    teamtailor,
    workable,
)

CONNECTORS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "smartrecruiters": smartrecruiters,
    "recruitee": recruitee,
    "teamtailor": teamtailor,
    "workable": workable,
    "remoteok": remoteok,
}
