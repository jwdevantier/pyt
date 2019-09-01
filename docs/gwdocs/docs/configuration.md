# Configuration

When running Ghostwriter, it will look for a `ghostwriter.conf.yml` configuration file in the current folder. This file will determine which files to process, the snippet syntax used, and so on. For example, consider this configuration file:

```yaml
parser:
  open: '<@@'
  close: '@@>'
  processes: 5
  temp_file_suffix: '.gw.tmp'
  include_patterns:
    - '.*\.go$'
  ignore_patterns:
    - '.*\.tpl\.go$'
  ignore_dir_patterns:
    - '.*/node_modules$'
    - '.*/\.git$'
    - '.*/venv$'
    - '.*/[^/]+\.egg-info$'
  search_paths:
    - ./cgen

logging:
  level: info
  format: '%(asctime)s - %(message)s'
  datefmt: '%Y-%m-%d %H:%M:%S'
```

## Parser Configuration
The `parser` section configures all aspects of how file parsing is handled. Generally, this section determines which files are monitored and if any of those are changed, the compilation phase is triggered. This section determines which files will be monitored, the syntax used for snippets, the degree of parallelism used and so on.

### Snippet syntax
The `open` and `close` settings determine how [snippets](2-snippets.md) are opened and closed. If omitted, the defaults of `<@@` and `@@>` is used.

Given:
```yaml
parser:
  open: '<<'
  close: '>>'
```

Snippets would look like so:
```text
    // some comment - these are language-specific
    // <<package.module.my_snippet>>
    // <</package.module.my_snippet>>
```

### Parallelism / performance
Ghostwriter spawns processes during compilation. This partly works around issues with Python imports and stale code, partly addresses the issues of parallelism with Python. 
For small projects, a single process will often suffice, but for very large projects such as the Linux kernel, using multiple processes can reduce the compilation time significantly.

To adjust the number of processes used during compilation, simply adjust `processes`.
```yaml
parser:
  # spawn 5 processes during compilation
  processes: 5
```

### File monitoring
Ghostwriter recursively scans and inspect all files from the project folder and down. Not all files are monitored, instead 3 configuration settings, each a list of regexes is used to determine whether a file is monitored or ignored.
In essence the precedence of these checks is `ignore_dir_patterns` > `ignore_patterns` > `include_patterns` and the default policy is to not monitor a file.

During compilation, the directories are recursively explored, however, any directory matching any of the `ignore_dir_patterns` is disregarded entirely. For each file found, it is first matched against the patterns in `ignore_patterns` and ignored if there is a match. Only then is the file matched against `include_patterns`, and only if it matches a pattern there will it be monitored and recompiled as necessary.

This approach makes it easy to pinpoint interesting files by pruning entire directory trees like `node_modules`, writing quite general patterns in `include_patterns` and using `ignore_patterns` to exclude specific files which would otherwise be included.

Finally, the default policy of ignoring files is to avoid the trouble of providing an exhaustive list of filetypes to ignore (zip, tar.gz, png, ...) in addition to plain better performance during compilation.

All paths tested are specified as *relative to the project root*, this ensures the base path cannot possibly affect matching. Thus, when parsing `/home/joe/work/project-x/lexer/lexer.go` in the project `/home/joe/work/project-x`, the path tested is `lexer/lexer.go`.

To test patterns, try pasting several example paths into [www.pythex.org](www.pythex.org) and starting writing the regex.

#### Summary

* All paths tested are relative to the project root
    * e.g. `/home/joe/project.x/lexer/lexer.go` tests `lexer/lexer.go`
* Precedence of evaluation is:
    * `ignore_dir_patterns` > `ignore_patterns` > `include_patterns`
* Files are ignored by default, `include_patterns` acts as a whitelist
* All 3 settings are lists of regex patterns.
* Temporary files (`temp_file_suffix`) are always ignored
* Test your patterns at [www.pythex.org](www.pythex.org) or use a similar tool

### Search paths
Search paths are additional directories you would like to scan when resolving snippets, technically, these paths are made available to all Python code from your snippets and beyond.

The entries can be absolute paths and as paths relative to the project root. Generally, relative paths are to be preferred because projects using these are more likely to work on other machines where the project is located somewhere else etc.

```yaml
parser:
  search_paths:
  # Absolute paths work - but be careful if you collaborate with others
  - /home/joe/common/my_py_project
  # Paths relative to the project root - use these!
  - ./ghostwriter
```

## Logging configuration
The `logging` section configures the format of log messages printed by Ghostwriter. The values shown above reflect the default format used if the section is omitted. 

If you want to override this, consult the Python `logging` modules' documenation, specifically the [LogRecord attributes](https://docs.python.org/3/library/logging.html#logrecord-attributes) section.
