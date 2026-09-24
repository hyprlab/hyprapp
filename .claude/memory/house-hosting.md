---
name: house-hosting
description: "Jason self-hosts many Docker containers on this machine; host 8000 is Portainer (never bind it); apps map host 8090+ -> container 8000 (8090-8099 full since 2026-09-24, Hyprfeed 8098); check docker ps before choosing a port; images go to Docker Hub as hyprlab/<app>, amd64 only"
metadata:
  type: user
---

Jason's machine is a self-hosting server running many Docker containers
(Portainer, Hyprfeed, tspro, luxel-web, viibestream and more). Host port 8000
belongs to Portainer: never bind it. The house convention maps host ports
8090 and up to container port 8000; Hyprfeed has **8098**. On 2026-09-24 the
whole 8090-8099 block was taken (tspro 8090, tspro-test 8091, hylki 8092,
ups-zonechart 8093, luxel-web 8094, tspro-demo 8095, tspro-backup 8096,
r-wiper 8097, hyprfeed 8098, dilbyrt 8099; viibestream is on 8080), so new
apps continue at 8100 and up. 5000-range host apps also exist. Check before
choosing:

```sh
docker ps --format '{{.Names}} {{.Ports}}'
```

Every Flask app is one Docker container with SQLite in a named volume at
`/data`. Images are published to Docker Hub as `hyprlab/<app>`, linux/amd64
only (the host's buildx has no arm64 builder). Source lives on GitHub under
`hyprlab/`. Everything is AGPL-3.0-or-later, © Hyprlab.

**How to apply:** the port a new app uses is set by `tools/init-project.sh`;
record it in the app's project memory. Related: [[ship-flow]].
