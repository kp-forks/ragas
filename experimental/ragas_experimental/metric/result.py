"""MetricResult object to store the result of a metric"""

__all__ = ["MetricResult"]

import typing as t

from fastcore.utils import patch
from pydantic import GetCoreSchemaHandler, ValidationInfo
from pydantic_core import core_schema


class MetricResult:
    """Class to hold the result of a metric evaluation.

    This class behaves like its underlying result value but still provides access
    to additional metadata like reasoning.

    Works with:
    - DiscreteMetrics (string results)
    - NumericMetrics (float/int results)
    - RankingMetrics (list results)
    """

    def __init__(
        self,
        result: t.Any,
        reason: str,
        traces: t.Optional[t.Dict[str, t.Any]] = None,
    ):
        if traces is not None:
            invalid_keys = [
                key for key in traces.keys() if key not in {"input", "output"}
            ]
            if invalid_keys:
                raise ValueError(
                    f"Invalid keys in traces: {invalid_keys}. Allowed keys are 'input' and 'output'."
                )
        self._result = result
        self.reason = reason
        self.traces = traces

    def __repr__(self):
        return repr(self._result)

    # Access to underlying result
    @property
    def result(self):
        """Get the raw result value."""
        return self._result

    # String conversion - works for all types
    def __str__(self):
        return str(self._result)

    # Container-like behaviors for list results (RankingMetric)
    def __getitem__(self, key):
        if not hasattr(self._result, "__getitem__"):
            raise TypeError(
                f"{type(self._result).__name__} object is not subscriptable"
            )
        return self._result[key]

    def __iter__(self):
        if not hasattr(self._result, "__iter__"):
            raise TypeError(f"{type(self._result).__name__} object is not iterable")
        return iter(self._result)

    def __len__(self):
        if not hasattr(self._result, "__len__"):
            raise TypeError(f"{type(self._result).__name__} has no len()")
        return len(self._result)

    # Numeric operations for numeric results (NumericMetric)
    def __float__(self):
        if isinstance(self._result, (int, float)):
            return float(self._result)
        raise TypeError(f"Cannot convert {type(self._result).__name__} to float")

    def __int__(self):
        if isinstance(self._result, (int, float)):
            return int(self._result)
        raise TypeError(f"Cannot convert {type(self._result).__name__} to int")

    def __add__(self, other):
        if not isinstance(self._result, (int, float)):
            raise TypeError(f"Cannot add {type(self._result).__name__} objects")
        if isinstance(other, MetricResult):
            return self._result + other._result
        return self._result + other

    def __radd__(self, other):
        if not isinstance(self._result, (int, float)):
            raise TypeError(f"Cannot add {type(self._result).__name__} objects")
        return other + self._result

    def __sub__(self, other):
        if not isinstance(self._result, (int, float)):
            raise TypeError(f"Cannot subtract {type(self._result).__name__} objects")
        if isinstance(other, MetricResult):
            return self._result - other._result
        return self._result - other

    def __rsub__(self, other):
        if not isinstance(self._result, (int, float)):
            raise TypeError(f"Cannot subtract {type(self._result).__name__} objects")
        return other - self._result

    def __mul__(self, other):
        if not isinstance(self._result, (int, float)):
            raise TypeError(f"Cannot multiply {type(self._result).__name__} objects")
        if isinstance(other, MetricResult):
            return self._result * other._result
        return self._result * other

    def __rmul__(self, other):
        if not isinstance(self._result, (int, float)):
            raise TypeError(f"Cannot multiply {type(self._result).__name__} objects")
        return other * self._result

    def __truediv__(self, other):
        if not isinstance(self._result, (int, float)):
            raise TypeError(f"Cannot divide {type(self._result).__name__} objects")
        if isinstance(other, MetricResult):
            return self._result / other._result
        return self._result / other

    def __rtruediv__(self, other):
        if not isinstance(self._result, (int, float)):
            raise TypeError(f"Cannot divide {type(self._result).__name__} objects")
        return other / self._result

    # Comparison operations - work for all types with same-type comparisons
    def __eq__(self, other):
        if isinstance(other, MetricResult):
            return self._result == other._result
        return self._result == other

    def __lt__(self, other):
        if isinstance(other, MetricResult):
            return self._result < other._result
        return self._result < other

    def __le__(self, other):
        if isinstance(other, MetricResult):
            return self._result <= other._result
        return self._result <= other

    def __gt__(self, other):
        if isinstance(other, MetricResult):
            return self._result > other._result
        return self._result > other

    def __ge__(self, other):
        if isinstance(other, MetricResult):
            return self._result >= other._result
        return self._result >= other

    # Method forwarding for type-specific behaviors
    def __getattr__(self, name):
        """Forward attribute access to the result object if it has that attribute.

        This allows calling string methods on discrete results,
        numeric methods on numeric results, and list methods on ranking results.
        """
        if hasattr(self._result, name):
            attr = getattr(self._result, name)
            if callable(attr):
                # If it's a method, wrap it to return MetricResult when appropriate
                def wrapper(*args, **kwargs):
                    result = attr(*args, **kwargs)
                    # If the result is of the same type as self._result, wrap it
                    if isinstance(result, type(self._result)):
                        return MetricResult(result=result, reason=self.reason)
                    return result

                return wrapper
            return attr
        raise AttributeError(f"{type(self).__name__} has no attribute '{name}'")

    # JSON/dict serialization
    def to_dict(self):
        """Convert the result to a dictionary."""
        return {"result": self._result, "reason": self.reason}


@patch(cls_method=True)
def validate(cls: MetricResult, value: t.Any, info: ValidationInfo):
    """Provide compatibility with older Pydantic versions."""
    if isinstance(value, MetricResult):
        return value
    return MetricResult(result=value)


@patch
def __json__(self: MetricResult):
    """Return data for JSON serialization.

    This method is used by json.dumps and other JSON serializers
    to convert MetricResult to a JSON-compatible format.
    """
    return {
        "result": self._result,
        "reason": self.reason,
    }


@patch(cls_method=True)
def __get_pydantic_core_schema__(
    cls: MetricResult, _source_type: t.Any, _handler: GetCoreSchemaHandler
) -> core_schema.CoreSchema:
    """Generate a Pydantic core schema for MetricResult.

    This custom schema handles different serialization behaviors:
    - For model_dump(): Returns the original MetricResult instance
    - For model_dump_json(): Converts to a JSON-compatible dict using __json__
    """

    def serializer_function(instance, info):
        """Handle different serialization modes for MetricResult."""
        # For JSON serialization (model_dump_json), use __json__ method
        if getattr(info, "mode", None) == "json":
            return instance.__json__()
        # For Python serialization (model_dump), return the instance itself
        return instance

    return core_schema.union_schema(
        [
            # First schema: handles validation of MetricResult instances
            core_schema.is_instance_schema(MetricResult),
            # Second schema: handles validation of other values and conversion to MetricResult
            core_schema.chain_schema(
                [
                    core_schema.any_schema(),
                    core_schema.no_info_plain_validator_function(
                        lambda value: (
                            MetricResult(result=value)
                            if not isinstance(value, MetricResult)
                            else value
                        )
                    ),
                ]
            ),
        ],
        serialization=core_schema.plain_serializer_function_ser_schema(
            serializer_function,
            info_arg=True,  # Explicitly specify that we're using the info argument
        ),
    )
