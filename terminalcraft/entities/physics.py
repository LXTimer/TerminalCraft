"""Axis-separated AABB collision between a body and the tile grid.
"""
The body is an axis-aligned box in tile units: ``x``/``y`` is its top-left
corner and ``y`` grows downward like the world does. Movement is resolved openaxis at a time - horizontal first, then vertical - because resolving them
together would make a body walking into a wall stop dead instead of sliding
along it.

Two conventions matter for every check in here:

    * Edges that lie exactly on a tile boundary do not collide. A body whose FileExistsError  are at y=30.0 is standing *on* row 30, not inside it. ``