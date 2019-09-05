import logging
logger = logging.getLogger(__name__)

from collections import Iterable
from six import string_types, class_types

from great_expectations.types import (
    RequiredKeysDotDict,
    AllowedKeysDotDict,
)

# TODO: Move this to great_expectations.types.base.py
class OrderedKeysDotDict(AllowedKeysDotDict):
    """extends AllowedKeysDotDict with a strict ordering of parameters.
    This make OrderedKeysDotDict behave somehwat like collections.namedtuples.

    OrderedKeysDotDicts...
        have an exactly-defined number of elements
        can parse from tuples
        coerce types by default
        raise an IndexError if args don't line up with keys

    See tests for examples.

    Lining up args with keys can be complex when key_types allow nesting.
    This logic is built into _zip_keys_and_args_to_dict.
    Again, see tests for examples.
    """

    _key_order = []

    def __init__(self, *args, **kwargs):
        logger.debug(self.__class__.__name__)
        assert set(self._key_order) == set(self._allowed_keys)
        assert set(self._key_order) == set(self._required_keys)

        coerce_types = kwargs.pop("coerce_types", True),
        if args == ():
            super(OrderedKeysDotDict, self).__init__(
                coerce_types=coerce_types,
                *args, **kwargs
            )

        else:
            new_kwargs = self._zip_keys_and_args_to_dict(args)
            super(OrderedKeysDotDict, self).__init__(
                coerce_types=coerce_types,
                **new_kwargs
            )

    @classmethod
    def _zip_keys_and_args_to_dict(cls, args):

        index = 0
        new_dict = {}
        for key in cls._key_order:
            try:
                if isinstance(args[index], dict):
                    increment = 1
                    new_dict[key] = args[index]

                else:
                    key_type = cls._key_types.get(key, None)
                    if isinstance(key_type, class_types) and issubclass(key_type, DataContextResourceIdentifier):
                        increment = key_type._recursively_get_key_length()
                        new_dict[key] = args[index:index+increment]
                    else:
                        increment = 1
                        new_dict[key] = args[index]

            except IndexError as e:
                raise IndexError("Not enough arguments in {0} to populate all fields in {1} : {2}".format(
                    args,
                    cls.__name__,
                    cls._key_order,
                ))

            index += increment

        if index < len(args):
            raise IndexError("Too many arguments in {0} to populate the fields in {1} : {2}".format(
                args,
                cls.__name__,
                cls._key_order,
            ))

        return new_dict

    @classmethod
    def _recursively_get_key_length(cls):
        key_length = 0

        for key in cls._key_order:
            key_type = cls._key_types.get(key, None)
            if isinstance(key_type, class_types) and issubclass(key_type, DataContextResourceIdentifier):
                key_length += key_type._recursively_get_key_length()
            else:
                key_length += 1
        
        return key_length

class DataContextResourceIdentifier(OrderedKeysDotDict):
    """is used to uniquely identify resources used by the DataContext.

    DataContextResourceIdentifier is based OrderedKeysDotDict.
    It extends the base class with a to_string method that converts
    the full, nested structure of the identifier into a string.

    For example:

        "DataAssetIdentifier.my_db.default_generator.my_table"
        "ValidationResultIdentifier.my_db.default_generator.my_table.default_expectations.warnings.prod.20190801"

    These strings are also used for hashing, so that DataContextResourceIdentifiers can be used in sets, etc.

    The parse_string_to_data_context_resource_identifier convenience method great_expectations.util
    can instantiate a valid identifier from any full identifier string.
    """

    def __init__(self, *args, **kwargs):
        # TODO : Pull out all of this logic into a `from_string` classmethod:
        from_string = kwargs.pop("from_string", None)

        if from_string == None:
            super(DataContextResourceIdentifier, self).__init__(
                *args, **kwargs
            )

        else:
        # /END TODO
            super(DataContextResourceIdentifier, self).__init__(
                *from_string.split(".")[1:],
                **kwargs
            )

    # TODO : Change this to __str__
    def to_string(self, include_class_prefix=True, separator="."):
        return separator.join(self._get_string_elements(include_class_prefix))

    # NOTE: This logic has been pulled into NamespacedReadWriteStore.
    # I'm not sure if we should keep a copy here.
    def _get_string_elements(self, include_class_prefix=True):
        string_elements = []

        if include_class_prefix:
            string_elements.append(self.__class__.__name__)

        for key in self._key_order:
            if isinstance( self[key], DataContextResourceIdentifier ):
                string_elements += self[key]._get_string_elements(include_class_prefix=False)
            else:
                string_elements.append(str(self[key]))

        return string_elements

    #This is required to make DataContextResourceIdentifiers hashable
    def __hash__(self):
        return hash(self.to_string())

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

class DataAssetIdentifier(DataContextResourceIdentifier):
    _key_order = [
        "datasource",
        "generator",
        "generator_asset"
    ]
    _key_types = {
        "datasource" : string_types,
        "generator" : string_types,
        "generator_asset" : string_types,
    }
    # NOTE: This pattern is kinda awkward. It would be nice to ONLY specify _key_order
    _required_keys = set(_key_order)
    _allowed_keys = set(_key_order)


class BatchIdentifier(DataContextResourceIdentifier):
    _key_order = [
        "data_asset_identifier",
        "batch_runtime_id",
    ]
    _key_types = {
        "data_asset_identifier" : DataAssetIdentifier,
        "batch_runtime_id" : string_types,
    }
    # NOTE: This pattern is kinda awkward. It would be nice to ONLY specify _key_order
    _required_keys = set(_key_order)
    _allowed_keys = set(_key_order)


# class RunIdentifier(DataContextResourceIdentifier):
#     _key_order = [
#         "execution_context",
#         "start_time_utc",
#     ]
#     _key_types = {
#         "execution_context" : string_types,
#         "start_time_utc" : int,
#     }
#     # NOTE: This pattern is kinda awkward. It would be nice to ONLY specify _key_order
#     _required_keys = set(_key_order)
#     _allowed_keys = set(_key_order)


class ExpectationSuiteIdentifier(DataContextResourceIdentifier):
    _key_order = [
        "data_asset_name",
        "expectation_suite_name",
    ]
    _key_types = {
        "data_asset_name" : DataAssetIdentifier,
        "expectation_suite_name" : string_types,
    }
    # NOTE: This pattern is kinda awkward. It would be nice to ONLY specify _key_order
    _required_keys = set(_key_order)
    _allowed_keys = set(_key_order)


class ValidationResultIdentifier(DataContextResourceIdentifier):
    _key_order = [
        "expectation_suite_identifier",
        "run_id",
        "batch_fingerprint"
        # "purpose"
    ]
    _key_types = {
        "expectation_suite_identifier" : ExpectationSuiteIdentifier,
        "run_id" : string_types,
        "batch_fingerprint": string_types
    }
    # NOTE: This pattern is kinda awkward. It would be nice to ONLY specify _key_order
    _required_keys = set(_key_order)
    _allowed_keys = set(_key_order)
