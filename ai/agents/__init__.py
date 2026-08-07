"""Specialized co-pilot agents.

Each subpackage owns one business capability and implements the shared agent
contract. Agents receive provider and storage dependencies through constructors;
this package initializer deliberately performs no eager imports or construction.
"""

__all__: tuple[str, ...] = ()
