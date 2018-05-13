# ARM64JSON

The repository contains ARM64 (AArch64) instruction encoding in a machine-readable JSON:

* `ISA_v83A_A64_xml_00bet6_instructions.json` contains encoding of every instruction, including ARM64v2/v3 extensions.
* `ISA_v83A_A64_xml_00bet6_group_class.json` contains hierarchical encoding ARM64 top level -> Instruction group (e.g. "Data Processing -- Immediate") -> Instruction class (e.g. "Add/subtract (immediate)"). No instruction encodings in this file.

The simple and easyly-organised JSON data was extracted from a machine-readable ARM64 specs. [A64 ISA XML for Armv8.3 ver. 00bet6.1](https://developer.arm.com/products/architecture/a-profile/exploration-tools) released by ARM.

**WARNING!** _I can't test every encoding from the JSON, so I can't promise they all are correct._

JSON file structure is obvious.

Also, see [ARM® Architecture Reference Manual (ARMv8, for ARMv8-A architecture profile) ver. C.a](https://developer.arm.com/docs/ddi0487/latest/arm-architecture-reference-manual-armv8-for-armv8-a-architecture-profile) for details.
