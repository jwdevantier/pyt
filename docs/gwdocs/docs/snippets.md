# Snippets

Snippets mark the regions of a file which contain generated code. Snippet syntax is loosely inspired by HTML in that there is a start- tag (e.g. `<@@my_module.my_snippet@@>`) and an end-tag (e.g. `<@@/my_module.my_snippet@@>`). The content between the tags is the output from last executing the snippet.

A snippet corresponds to some Python function of the form:
```python
def my_snippet(ctx: Context, prefix: str, fw: IWriter):
    ...
```

The snippet function can write directly to the file via the `IWriter` instance. Everything written via the interface will follow the opening snippet tag. The `prefix` string contains the leading whitespace from the snippet opening line. Use `prefix` to indent each snippet line to match its context.

## Example
Resolving a snippet name to a Python function closely follows the notation for regular imports. Thus the snippet:

```text
   <@@package1.package2.module.my_snippet@@>
   <@@/package1.package2.module.my_snippet@@>
```

... is roughly equivalent to the following in Python:

```python
from package1.package2.module import my_snippet
my_snippet(some_context, '   ', file_handle)
```

Assuming the `my_snippet` implementation is this:

```python
def my_snippet(ctx: Context, prefix: str, fw: IWriter):
    fw.write(f"{prefix}hello")
    fw.write(", world!\n")
    fw.write("something else")
```

The final output in the file would be:
```text
   <@@package1.package2.module.my_snippet@@>
   hello, world!
something else
   <@@/package1.package2.module.my_snippet@@>
```

Some things to note:

* You are responsible for:
    * Inserting newline characters to separate lines
    * Using the `prefix` value to indent lines properly
* A trailing newline will be inserted if your code did not (as in this case)
* Any contents between the snippet tags is overwritten on next run


## Where to store the snippet code
Ghostwriter uses the standard Python import mechanism to locate snippet functions. Chiefly, Python uses the list of directories in `sys.path` to determine which directories to search and in what order when handling imports. Any directories added to the `search_paths` list in the configuration file are automatically appended to the standard list.
