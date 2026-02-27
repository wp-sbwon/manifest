#!/bin/bash
# Run calculator using actual modules (cli.parser, engine.calculator, output.formatter).
cd "$(dirname "$0")" && python -m main "$@"
