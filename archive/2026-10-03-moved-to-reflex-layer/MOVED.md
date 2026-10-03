# Moved to reflex-layer on 2026-10-03

The cognitive executive and everything measured with it now live in
[reflex-layer](https://github.com/lucascosolo/reflex-layer) (owner's suggestion, 2026-10-03):
`executive/`, `tests/test_executive/`, `bench/pilot/` (E2–E7b), the pilot results, the
architecture doc and reports (`docs/executive/`), and the review packet. reflex-layer is the
maintained copy; new work happens there.

This folder is the frozen copy that was here, moved with `git mv` so history follows it. Nothing
was deleted, per the project's safety rule. It is no longer collected by brain-sim's tests
(`pytest.ini` collects `tests/` only) and nothing imports it. **It can be deleted manually by the
owner** once the reflex-layer copy is accepted; no agent will do that.

What stays in brain-sim: the spiking-simulation research (`brainsim/`, `server/`, `ui/`, `tests/`,
`docs/recovery/`), and `tests/test_safety_lint.py`, which lints this repository with reflex-layer's
`tools/safety_lint.py`.
