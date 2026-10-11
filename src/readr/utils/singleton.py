from typing import Any, ClassVar


class SingletonMeta(type):
    """
    A metaclass for creating singleton classes.

    It ensures that only one instance of a class is created,
    regardless of how many times the class is instantiated.
    Arguments passed after the first instantiation are ignored.
    """

    _instances: ClassVar[dict[type, object]] = {}

    def __call__(cls, *args: Any, **kwargs: Any):
        """
        Returns the single instance of the class, creating it on first use.

        Args:
            *args (Any): Positional arguments for the class constructor (first call only).
            **kwargs (Any): Keyword arguments for the class constructor (first call only).

        Returns:
            The one instance of the class.
        """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]
