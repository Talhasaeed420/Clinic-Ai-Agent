from bson import ObjectId
from pydantic_core import core_schema

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        def validate(value):
            if isinstance(value, ObjectId):
                return value
            if isinstance(value, str):
                try:
                    return ObjectId(value)
                except Exception:
                    raise ValueError("Invalid ObjectId")
            raise ValueError("Must be string or ObjectId")

        return core_schema.no_info_after_validator_function(
            validate,
            core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.str_schema()
            ])
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, _core_schema, handler):
        return handler(core_schema.str_schema())
