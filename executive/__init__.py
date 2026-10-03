"""brain-sim's cognitive executive: goals, world state, prediction, action selection, memory.

The loop in loop.py is ordinary code. Language models appear only as Deliberators
(deliberation.py), called at an explicit impasse with a bounded projection of the state.
Every effect on the world goes through reflex-layer's permissioned capability registry.
"""
