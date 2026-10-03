# brain-sim — recovery baseline

Created 2026-10-02 from files rebuilt out of Remote Control session transcripts after the home-directory wipe on lucas-pc. This is not the full project: the original source tree is still being recovered from disk and will be added as it is identified. See the recovery notes in the repository history.

## 2026-10-03: files carved from git objects

Fourteen recovered git packfiles plus loose objects (bare repo on the recovery card) held 12 brain-sim
commits (SPEC 8.9 → 8.47, 13 Sep – 1 Oct 2026) but only 13 of their files' contents. Those 13 are added
here at their original paths (SPEC.md, brainsim/{engine,inhib,params,worker}.py, seven tests, ui/stage1_results.json);
each comes from the newest carved commit that still had it (dates per path in
docs/recovery/carved-manifest-2026-10-03.tsv), so they may be older than master's last state.
docs/recovery/carved-commit-log-2026-10-03.md lists every carved commit with its full message and which
blobs survived. Master c9863d6 and the branches gen2, pending-express, plateau-override, deficit-diag,
joint-confirm and persist-dual were not among the carved objects.
