# core/database/peewee_repositories/base_repository.py
from typing import TypeVar, Generic, Optional, List, Type
from peewee import Model, ModelSelect

T = TypeVar('T', bound=Model)

class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    def get_by_id(self, id_value: any) -> Optional[T]:
        return self.model.get_or_none(self.model._meta.primary_key == id_value)

    def get_all(self, limit: int = None, offset: int = None) -> List[T]:
        query = self.model.select()
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        return list(query)