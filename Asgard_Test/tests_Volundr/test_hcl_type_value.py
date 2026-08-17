"""CH-0108 leftover: HCL type/value cannot break out of the block."""

import pytest

from Asgard.Volundr.Terraform.models.terraform_models import (
    CloudProvider,
    ModuleConfig,
    OutputConfig,
    ResourceCategory,
    VariableConfig,
)
from Asgard.Volundr.Terraform.services._module_builder_generators import (
    generate_outputs_tf,
    generate_variables_tf,
)


def test_newline_in_variable_type_is_refused():
    config = ModuleConfig(
        name="mod",
        provider=CloudProvider.AWS,
        category=ResourceCategory.COMPUTE,
        variables=[VariableConfig(name="x", type="string\n}\nresource \"x\" {}", description="d")],
    )
    with pytest.raises(ValueError, match="type"):
        generate_variables_tf(config)


def test_hash_in_output_value_is_refused():
    config = ModuleConfig(
        name="mod",
        provider=CloudProvider.AWS,
        category=ResourceCategory.COMPUTE,
        outputs=[OutputConfig(name="out", value="var.x\n# pwned", description="d")],
    )
    with pytest.raises(ValueError, match="output value"):
        generate_outputs_tf(config)
