"""Runtime configuration and dependency-composition package.

Modules in this package have distinct responsibilities:

* ``settings`` validates environment-supplied configuration.
* ``logging`` configures structured application logging.
* ``container`` constructs and owns concrete application dependencies.

Nothing is imported eagerly here. That keeps ``import ai.config`` free from
environment validation, model loading, filesystem access, and other side effects.
Consumers should import the specific object they require from its defining module.
"""

__all__: tuple[str, ...] = ()
