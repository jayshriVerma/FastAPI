from abc import ABC, abstractmethod
from typing import Dict, Optional


class UserRepository(ABC):
    """
    An Async Repository Interface
    This is a contract, not an implementation.
    Methods defined here should be implemented by any concrete repository class.
    """

    @abstractmethod
    async def create_user(self, user: Dict) -> None: ...

    @abstractmethod
    async def get_user(self, username: str) -> Optional[Dict]: ...

    @abstractmethod
    async def add_tag(self, username: str, tag: str) -> Dict: ...


# API does not care where data is stored
# can replace memory with DB later without touching routes
