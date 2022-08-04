# 0.9.0 (2022-08-04)
* use gzip to compress pickle artifacts

# 0.8.0 (2022-02-02)
* use common exception class `AutoMockException`

# 0.7.0 (2020-04-22)
* reduce memory keys to instance index and call index pairs
* introduce rich `Call` object
* use pickle to pack `args` and `kwargs`, so comparision is more strict than with `repr`
* add debug callback argument and `pdb` fallback
* more informative error messages

# 0.6.3 (2019-12-27)
* reduce exception content with `reprlib`

# 0.6.2 (2019-12-18)
* catch encoding exceptions
* add pypi autodeploy

# 0.6.1 (2019-12-12)
* prettify error message

# 0.6.0 (2019-12-12)
* add support for mocking builtins
* add `--automock-remove` cli argument
* add support for targeting with module path
* fix coverage report on travis

# 0.5.0 (2019-12-11)
* fix/add multiple instances support

Thanks to [Roman Tolkachyov](https://github.com/romantolkachyov)

# 0.4.0 (2019-12-02)
* remove allowed/forbidden lists since complexity
* add result serialization to prevent mutations

# 0.3.0 (2019-11-12)
* add python 3.6 support

# 0.2.0 (2019-11-09)
* allow to override filename
* add black and white method lists
* add customizable encode/decode routines

# 0.1.1 (2019-11-08)
* add functions support

# 0.1.0 (2019-11-08)
* initial release
