# ORE Installation Guide for macOS

This guide provides detailed instructions for installing and building Open Source Risk Engine (ORE) on macOS.

## Quick Start

For experienced users who want to build immediately:

```bash
# Install dependencies
brew install cmake boost ninja

# Build with Ninja (fastest)
mkdir -p build && cd build
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release
ninja

# Run tests
ctest -j $(sysctl -n hw.ncpu)
```

For detailed instructions, see the sections below.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Installing Dependencies](#installing-dependencies)
- [Building ORE](#building-ore)
- [Build Options](#build-options)
- [Troubleshooting](#troubleshooting)
- [Running Tests](#running-tests)
- [Next Steps](#next-steps)

## Prerequisites

### System Requirements

- macOS 10.15 (Catalina) or later
- Xcode Command Line Tools or full Xcode
- At least 4 GB of RAM (8 GB recommended)
- At least 5 GB of free disk space

### Required Tools

- CMake 3.15 or higher
- C++ compiler with C++17 support (Clang from Xcode)
- Boost libraries (version 1.58 or higher)
- Git (for version control)

## Installing Dependencies

### 1. Install Xcode Command Line Tools

If you haven't already installed Xcode Command Line Tools:

```bash
xcode-select --install
```

Verify installation:

```bash
clang++ --version
```

### 2. Install Homebrew

If you don't have Homebrew installed:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 3. Install CMake

```bash
brew install cmake
```

Verify installation:

```bash
cmake --version
```

You should see version 3.15 or higher.

### 4. Install Boost

ORE requires Boost libraries. Install using Homebrew:

```bash
curl -LO https://archives.boost.io/release/1.85.0/source/boost_1_85_0.tar.gz
tar -xzf boost_1_85_0.tar.gz
cd boost_1_85_0v
./bootstrap.sh --prefix=/usr/local
sudo ./b2 -j8 install
```

This will install Boost in `/opt/homebrew/` (Apple Silicon) or `/usr/local/` (Intel).

Verify installation:

```bash
ls /usr/local/include/boost
```

### 5. Optional Dependencies

For Python integration (optional):

```bash
brew install python3
brew install swig
```

For compression support:

```bash
brew install zlib
```

For faster builds with Ninja (recommended):

```bash
brew install ninja
```

Verify installation:

```bash
ninja --version
```

**Why Ninja?** Ninja is a small build system focused on speed. It can build ORE 30-50% faster than Make by optimizing parallel execution and minimizing overhead. Highly recommended for development workflows with frequent rebuilds.

## Building ORE

### 1. Clone the Repository

If you haven't already cloned the repository:

```bash
git clone <your-ore-repository-url>
cd ORE
```

If you already have the repository, make sure submodules are initialized:

```bash
git submodule update --init --recursive
```

### 2. Create Build Directory

```bash
mkdir -p build-release
mkdir -p build-debug
```

### 3. Configure the Build

#### Basic Configuration

For a standard build with all components:

```bash
cd build-debug
cmake ..
```

#### Configuration with Options

You can customize the build with various options:

```bash
cmake .. -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DBoost_INCLUDE_DIR=/usr/local/include \
  -DBoost_LIBRARY_DIR=/usr/local/lib

cmake .. -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DBoost_INCLUDE_DIR=/usr/local/include \
  -DBoost_LIBRARY_DIR=/usr/local/lib
```

#### Using Ninja Build System (Faster)

For significantly faster builds, use Ninja instead of Make:

```bash
cmake .. -G Ninja
```

You can combine this with other options:

```bash
cmake .. -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DORE_BUILD_DOC=OFF \
  -DORE_BUILD_EXAMPLES=ON \
  -DORE_BUILD_TESTS=ON
```

#### For Apple Silicon (M1/M2/M3) Macs

If you encounter architecture-related issues:

```bash
cmake .. -DCMAKE_OSX_ARCHITECTURES=arm64
```

Or with Ninja:

```bash
cmake .. -G Ninja -DCMAKE_OSX_ARCHITECTURES=arm64
```

### 4. Build ORE

#### Using Make (Default)

Build with all available CPU cores:

```bash
cmake --build . -j $(sysctl -n hw.ncpu)
```

#### Using Ninja (Recommended for Speed)

If you configured with `-G Ninja`:

```bash
ninja -j 8
```

The build process will compile:
- QuantLib (the quantitative finance library)
- QuantExt (QuantLib extensions)
- OREData (data layer)
- OREAnalytics (analytics layer)
- App (ORE application)

**Build time:** This may take 15-45 minutes with Make, or 10-30 minutes with Ninja, depending on your hardware.

## Build Options

You can customize the build using CMake options. Here are the available options:

| Option | Default | Description |
|--------|---------|-------------|
| `ORE_BUILD_DOC` | ON | Build documentation |
| `ORE_BUILD_EXAMPLES` | ON | Build examples |
| `ORE_BUILD_TESTS` | ON | Build test suite |
| `ORE_BUILD_APP` | ON | Build ORE application |
| `ORE_BUILD_SWIG` | ON | Build ORE Python bindings |
| `ORE_USE_ZLIB` | OFF | Use compression for boost::iostreams |
| `ORE_PYTHON_INTEGRATION` | OFF | Build ORE with Python Integration |
| `QL_USE_PCH` | OFF | Use precompiled headers |
| `CMAKE_BUILD_TYPE` | RelWithDebInfo | Build type (Debug, Release, RelWithDebInfo) |

### Example: Minimal Build

For a faster build without tests and examples:
```bash
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DORE_BUILD_DOC=OFF \
  -DORE_BUILD_EXAMPLES=OFF \
  -DORE_BUILD_TESTS=OFF

cmake --build . -j $(sysctl -n hw.ncpu)
```

With Ninja (faster):

```bash
cmake .. -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DORE_BUILD_DOC=OFF \
  -DORE_BUILD_EXAMPLES=OFF \
  -DORE_BUILD_TESTS=OFF

ninja -j 8
```

### Clean Build

If you need to start over:

```bash
cd build
rm -rf *
cmake ..
cmake --build . -j $(sysctl -n hw.ncpu)
```

### Linker Warnings

You may see linker warnings about flat namespace. These are typically harmless on macOS and can be ignored. ORE uses `-flat_namespace` to align behavior with Linux.

## Running Tests

After building, you can run the test suites to verify the installation:

### QuantLib Tests

```bash
cd build/QuantLib/test-suite
./quantlib-test-suite
```

### QuantExt Tests

```bash
cd build/QuantExt/test
./quantext-test-suite
```

### OREData Tests

```bash
cd build/OREData/test
./ored-test-suite
```

### OREAnalytics Tests

```bash
cd build/OREAnalytics/test
./orea-test-suite
```

### Run All Tests Using CTest

From the build directory:

```bash
ctest -j $(sysctl -n hw.ncpu)
```

For verbose output:

```bash
ctest -V
```

## Running the ORE Application

After a successful build, the ORE executable is located at:

```bash
build/App/ore
```

To run ORE on the example inputs:

```bash
cd Examples/Example_1
../../build/App/ore ore.xml
```

## Next Steps

### Documentation

- Read the User Guide: `Docs/userguide.pdf`
- Explore the API Reference: `Docs/ore_design.pdf`
- Check the product documentation: `Docs/products.pdf`

### Examples

The `Examples/` directory contains numerous examples demonstrating ORE's capabilities:

- **MinimalSetup**: Simple portfolio valuation
- **Exposure**: Exposure calculations
- **MarketRisk**: Market risk analytics
- **CreditRisk**: Credit risk calculations
- **InitialMargin**: Initial margin calculations

Each example includes a README explaining the setup and expected outputs.

### Python Integration

If you built with Python support, you can use ORE from Python:

```bash
cd Examples/ORE-Python
python3 -m pip install -r requirements.txt
jupyter notebook
```

### Development

For development work:

1. Consider building with `CMAKE_BUILD_TYPE=Debug` for better debugging
2. Enable all warnings and tests with `ORE_BUILD_TESTS=ON`
3. Use the test suites to validate your changes
4. Refer to `Docs/CodingStandards/` for code style guidelines

## Environment Variables

You may want to add the ORE binary to your PATH:

```bash
echo 'export PATH="$PATH:/path/to/ORE/build/App"' >> ~/.zshrc
source ~/.zshrc
```

## Performance Tips

### Use Ninja for Faster Builds

Ninja is significantly faster than Make for building ORE:

```bash
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release
ninja
```

Expect 30-50% faster build times compared to Make.

### Optimize for Production

For production builds with maximum optimization:

```bash
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release
ninja
```

### Use Precompiled Headers

For faster compilation using precompiled headers:

```bash
cmake .. -G Ninja -DQL_USE_PCH=ON
ninja
```

Note: Precompiled headers require additional disk space but can speed up compilation by 20-40%.

### Combine Performance Options

For the fastest possible build:

```bash
cmake .. -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DQL_USE_PCH=ON \
  -DORE_BUILD_DOC=OFF

ninja
```

## Additional Resources

- ORE Project Website: http://opensourcerisk.org
- QuantLib Website: http://quantlib.org
- GitHub Issues: Use for reporting bugs and requesting features
- User Guide: Comprehensive documentation in `Docs/userguide.pdf`

## License

ORE is released under the Modified BSD License. See [LICENSE.txt](license.txt) for details.

## Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review the documentation in the `Docs/` directory
3. Search existing GitHub issues
4. Create a new issue with:
   - Your macOS version
   - CMake version
   - Compiler version
   - Complete error messages
   - Build configuration used


