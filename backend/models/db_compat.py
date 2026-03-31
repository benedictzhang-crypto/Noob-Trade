from sqlalchemy import BigInteger, Integer, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import JSON, TypeDecorator


COMPAT_BIGINT = BigInteger().with_variant(Integer, "sqlite")


class StringListType(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.ARRAY(Text))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return []
        return list(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        return list(value)
