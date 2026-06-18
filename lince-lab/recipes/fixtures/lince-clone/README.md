# lince-clone fixture (placeholder)

This directory is the **single host workspace** that the `lince-wizard` and
`lince-installer` recipes stage into the disposable VM (`[workspace].host_dir`).

It is intentionally minimal: on a real KVM run the lince repo / quickstart
sources are staged here (or this placeholder is overlaid by the bisect loop's
per-candidate checkout). Keeping a committed placeholder means `host_dir`
resolves to an existing directory under the recipe dir, so `recipe.validate`
passes in this VM-less sandbox and `recipe.run` has something to `copy_in`.

Do not put secrets here — the broker copy-in policy bounds staging to this dir
and strips host credential locations.
