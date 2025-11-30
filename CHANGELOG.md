# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-30

### Added
- Initial release of CPU Direct USB Checker for Linux
- Detect USB controller type (CPU-direct vs Chipset)
- Detect USB hubs in the device path
- Color-coded terminal output
- Command-line interface
- Comprehensive test suite
- Type checking with mypy
- Code formatting with black and isort

### Changed
- Improved exception handling with specific exception types
- Added type annotations throughout the codebase
- Updated mypy configuration for better compatibility

### Fixed
- Bare except clauses replaced with specific exceptions