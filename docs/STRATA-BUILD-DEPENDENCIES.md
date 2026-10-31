# Strata repair build: dependency recovery

Run on a Mac with full Xcode:

```bash
bash tools/bootstrap-strata-deps.sh --check
bash tools/bootstrap-strata-deps.sh --install
```

The script checks tools, initializes the pinned submodules, fetches the exact hashed llvm-mingw archive, and checks out the pinned LLVM source. It deliberately **does not** claim to create LLVM's compiled iOS/host outputs or private Microsoft/Apple dependencies. Follow `docs/BUILDING.md` for those build stages.

Microsoft VC++ DLLs must come from a legitimate Microsoft redistributable or authorized Windows installation; do not commit them to this repository. The Metal Shader Converter installer may require access through Apple's developer downloads if rebuilding it, and the existing tracked converter library should be reused where permitted.

Do not update the pinned submodules to newer commits to sidestep checkout failures: they contain Madeira-specific modifications. If a pinned revision is absent remotely, it must be restored or upstreamed from the original development environment.

Strata JIT uses the **host process** debugger. Do not remove the built-in helper's LiveContainer guard: this would not make a guest extension launch. Compile first, then use the custom Madeira JIT script in Strata and test the Wine bind fallback.

This is dependency preparation, not a verified app build.
