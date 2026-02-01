
from ...schemas import SCHEMA, schema_property_plugin, apply_schema_property, bind_schema_property
from gedcomtools.gedcomx.person import Person


def argo_description_get(self) -> str:
    return self.names[0].nameForms[0].fullText

def argo_description_set(self, value: str) -> None:
    self.names[0].nameForms[0].fullText = value

bind_schema_property(
    Person,
    argo_description_get,
    fset=argo_description_set,
    name="argo_description",
    schema=SCHEMA,
)
