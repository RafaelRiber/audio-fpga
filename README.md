### Usage
- [Install uv](https://github.com/astral-sh/uv?tab=readme-ov-file#installation)
```
git clone https://github.com/RafaelRiber/uv-amaranth.git
cd uv-amaranth
uv run <target> 
```
Current targets:
- icebreaker board (ice40up5k)

For example:
```
uv run build_icebreaker
openFPGALoader -b ice40_generic build/top.bin
```

### Tests
To run the tests located in the tests/ directory, use uv to run pytest:
```
uv run -m pytest
```





