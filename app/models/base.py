from sqlalchemy.ext.declarative import as_declarative, declared_attr
import re
import inflect

p = inflect.engine()

def camel_to_snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

@as_declarative()
class Base:
    id: int
    __name__: str

    @declared_attr
    def __tablename__(cls) -> str:
        return p.plural(camel_to_snake(cls.__name__))
