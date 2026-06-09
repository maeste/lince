---
id: m-16
title: "m-16: Config v2 — policy layer + unified registry"
---

## Description

Replace scattered configuration (~15 surfaces) with a policy-layer architecture: ~/.config/lince/lince.toml (user intent, versioned, default-deny), registry.d/ (shipped agent registry, one file per agent, always overwritten), generated mechanism outputs, and a single resolution point exposed via `lince config resolve --json`. GitHub epic: RisorseArtificiali/lince#200. Depends on m-14 (lince CLI). Members: GH #201-#205 + existing #199, #108 (LINCE-117).
