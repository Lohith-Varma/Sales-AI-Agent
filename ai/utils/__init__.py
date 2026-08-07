"""Small, dependency-light helpers shared by application components.

Utilities must not contain agent policy, provider clients, mutable global state, or
application composition. Import the required helper from its defining module so
dependencies remain explicit and package import stays free of side effects.
"""

__all__: tuple[str, ...] = ()
