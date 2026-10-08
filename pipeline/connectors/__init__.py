"""One module per hiring system. Each exposes parse(data, board) and async fetch(client, board)."""

from pipeline.connectors import ashby, greenhouse, lever, smartrecruiters

CONNECTORS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "smartrecruiters": smartrecruiters,
}
